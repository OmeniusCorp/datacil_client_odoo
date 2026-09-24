from odoo.tests import tagged

from odoo.addons.datacil_client_odoo.tests.common import CREDITS_PAYLOAD, DatacilTestCommon

VEHICLE_PAYLOAD = {
    'status': 200, 'success': True, 'message': 'Vehiculo encontrado', 'timestamp': 1,
    'data': {
        'placa': 'PBX1234',
        'vehiculo': {'marca': 'TOYOTA', 'modelo': 'HILUX', 'anio': 2021, 'color': 'BLANCO', 'chasis': 'MR0FB8CD0M0123456',
                     'combustible': 'GASOLINA', 'transmision': 'AUTOMATICA', 'asientos': 5, 'puertas': 4,
                     'clase': 'CAMIONETA', 'servicio': 'PARTICULAR', 'avaluo': '18.500,00',
                     'fechaMatricula': '15/03/2021', 'ultimaMatricula': '2025'},
        'propietario': {'cedula': '1710034065', 'nombre': 'MARTINEZ SILVA ANDREA LUCIA'},
        'deuda': {'total': 45.5},
        'citaciones': [{'id': 'C1'}],
        'bloques': {'vehiculo': 'ok', 'propietario': 'ok'},
    },
    'meta': {},
}


# The API documents the endpoint but not the shape of each block: some answers
# carry counters and nested dicts instead of plain lists.
VEHICLE_DICT_PAYLOAD = {
    'status': 200, 'success': True, 'message': 'Vehiculo encontrado', 'timestamp': 1,
    'data': {
        'placa': 'EAA1150',
        'vehiculo': {'marca': {'nombre': 'CHEVROLET'}, 'modelo': 'AVEO', 'anio': '2015', 'color': 'ROJO'},
        'propietario': {'cedula': {'valor': '1710034065'}, 'nombre': 'JUAN PEREZ'},
        'citaciones': {'total': 3, 'items': [{'id': 'C1'}]},
        'deuda': {'valorTotal': '78,50'},
        'bloques': {'citaciones': 'ok'},
    },
    'meta': {},
}


@tagged('post_install', '-at_install', 'datacil')
class TestFleetVehicleDatacil(DatacilTestCommon):

    def test_lookup_new_vehicle_values(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Toyota'})
        model = self.env['fleet.vehicle.model'].create({'name': 'Hilux', 'brand_id': brand.id})
        owner = self.env['res.partner'].create({'name': 'Andrea', 'vat': '1710034065'})
        with self.mock_get([self.ok(VEHICLE_PAYLOAD), self.ok(CREDITS_PAYLOAD)]) as calls:
            # Row labels are translated: read them in English to assert on them.
            result = self.env['fleet.vehicle'].with_context(lang='en_US').datacil_lookup_vehicle('pbx-1234')
        self.assertTrue(result['success'], result)
        self.assertTrue(calls[0][0].endswith('/ecuador/data/vehiculo/PBX1234'))
        values = result['values']
        self.assertEqual(values['vin_sn'], 'MR0FB8CD0M0123456')
        self.assertEqual(values['color'], 'BLANCO')
        self.assertEqual(values['model_year'], '2021')
        self.assertEqual(values['model_id']['id'], model.id)
        self.assertEqual(values['driver_id']['id'], owner.id)
        self.assertEqual(values['license_plate'], 'PBX1234')
        self.assertEqual(values['fuel_type'], 'gasoline')
        self.assertEqual(values['transmission'], 'automatic')
        self.assertEqual(values['seats'], 5)
        self.assertEqual(values['doors'], 4)
        self.assertEqual(values['car_value'], 18500.0)
        self.assertEqual(values['acquisition_date'], '2021-03-15')
        self.assertEqual(values['datacil_vehicle_class'], 'CAMIONETA')
        self.assertEqual(values['datacil_service_type'], 'PARTICULAR')
        self.assertEqual(values['datacil_last_registration'], '2025')
        self.assertEqual(values['datacil_owner_vat'], '1710034065')
        self.assertEqual(values['datacil_pending_fees'], 45.5)
        self.assertEqual(values['datacil_citation_count'], 1)
        self.assertIn('TOYOTA', values['datacil_info'])
        self.assertTrue(any(row['label'] == 'Driver' for row in result['rows']))

    def test_lookup_saved_vehicle_posts_note_and_keeps_driver(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Kia'})
        model = self.env['fleet.vehicle.model'].create({'name': 'Rio', 'brand_id': brand.id})
        driver = self.env['res.partner'].create({'name': 'Current driver'})
        vehicle = self.env['fleet.vehicle'].create({'model_id': model.id, 'license_plate': 'PBX1234', 'driver_id': driver.id})
        self.env['res.partner'].create({'name': 'Owner', 'vat': '1710034065'})
        with self.mock_get([self.ok(VEHICLE_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = vehicle.with_context(lang='en_US').datacil_lookup_vehicle()
        self.assertTrue(result['success'])
        self.assertNotIn('driver_id', result['values'], "An assigned driver is never replaced")
        # The vehicle is a Toyota Hilux in the payload: the catalog entry is created.
        created = self.env['fleet.vehicle.model'].browse(result['values']['model_id']['id'])
        self.assertEqual(created.name.upper(), 'HILUX')
        self.assertEqual(created.brand_id.name.upper(), 'TOYOTA', "An existing brand is reused whatever its casing")
        self.assertEqual(created.vehicle_type, 'car')
        self.assertTrue(vehicle.message_ids.filtered(lambda m: 'Datacil' in (m.body or '')))

    def test_dict_shaped_blocks(self):
        """Counters and nested dicts must not break the mapping."""
        with self.mock_get([self.ok(VEHICLE_DICT_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self.env['fleet.vehicle'].datacil_lookup_vehicle('EAA1150')
        self.assertTrue(result['success'], result)
        values = result['values']
        self.assertEqual(values['datacil_citation_count'], 3, "Counter dict read as a count")
        self.assertEqual(values['datacil_pending_fees'], 78.5, "Amount dict with a comma decimal")
        self.assertEqual(values['datacil_owner_vat'], '1710034065', "Identification wrapped in a dict")
        self.assertEqual(values['color'], 'ROJO')
        self.assertEqual(values['model_year'], '2015')
        self.assertTrue(any(row['value'] == 'CHEVROLET' for row in result['rows']), result['rows'])

    def test_unexpected_payload_is_not_fatal(self):
        """A shape we cannot map still returns the data instead of raising."""
        payload = dict(VEHICLE_PAYLOAD, data={'vehiculo': ['unexpected'], 'citaciones': 'n/a'})
        with self.mock_get([self.ok(payload), self.ok(CREDITS_PAYLOAD)]):
            result = self.env['fleet.vehicle'].datacil_lookup_vehicle('EAA1150')
        self.assertTrue(result['success'], result)
        self.assertTrue(result['values']['datacil_info'])
        self.assertTrue(any(row['value'] == 'EAA1150' for row in result['rows']))

    def test_model_is_created_once_and_bikes_are_detected(self):
        payload = dict(VEHICLE_PAYLOAD)
        payload['data'] = dict(VEHICLE_PAYLOAD['data'],
                               vehiculo={'marca': 'SUZUKI', 'modelo': 'GN125', 'clase': 'MOTOCICLETA'})
        with self.mock_get([self.ok(payload), self.ok(CREDITS_PAYLOAD)]):
            first = self.env['fleet.vehicle'].datacil_lookup_vehicle('PBX1234')
        with self.mock_get([self.ok(payload), self.ok(CREDITS_PAYLOAD)]):
            second = self.env['fleet.vehicle'].datacil_lookup_vehicle('PBX1234')
        self.assertEqual(first['values']['model_id']['id'], second['values']['model_id']['id'],
                         "The catalog entry is reused, not duplicated")
        self.assertEqual(self.env['fleet.vehicle.model'].browse(first['values']['model_id']['id']).vehicle_type, 'bike')

    def test_errors(self):
        self.assertEqual(self.env['fleet.vehicle'].datacil_lookup_vehicle('12')['code'], 'invalid')
        with self.mock_get([self.error(404, 'Vehiculo no encontrado')]):
            self.assertEqual(self.env['fleet.vehicle'].datacil_lookup_vehicle('PBX1234')['code'], 'not_found')
