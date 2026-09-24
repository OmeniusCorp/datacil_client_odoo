from odoo.tests import tagged

from odoo.addons.datacil_client_odoo.tests.common import CEDULA_PAYLOAD, CREDITS_PAYLOAD, DatacilTestCommon

LICENCE_PAYLOAD = {
    'status': 200, 'success': True, 'message': 'Licence found', 'timestamp': 1,
    'data': {
        'id': '1710034065', 'holder': 'MARTINEZ SILVA ANDREA LUCIA', 'hasLicence': True,
        'licences': [
            {'type': 'A', 'validFrom': '2015-01-01', 'validUntil': '2020-01-01', 'isActive': False},
            {'type': 'B', 'validFrom': '2024-12-03', 'validUntil': '2029-12-02', 'isActive': True},
        ],
        'points': {'current': 27.5, 'max': 30},
        'meta': {'partial': False, 'failed': [], 'generatedAt': '2026-08-24T12:00:00.000Z'},
    },
    'meta': {},
}
JUDICIAL_PAYLOAD = {'status': 200, 'success': True, 'message': 'Causas', 'timestamp': 1,
                    'data': {'causas': [{'idJuicio': '17230-2024-00001', 'rol': 'demandado', 'materia': 'CIVIL'}]}, 'meta': {}}
CITATIONS_PAYLOAD = {'status': 200, 'success': True, 'message': 'Citaciones', 'timestamp': 1,
                     'data': {'citaciones': [{'id': 'C1', 'valor': 30}, {'id': 'C2', 'valor': 60}]}, 'meta': {}}
DEBT_PAYLOAD = {'status': 200, 'success': True, 'message': 'Estado de cuenta', 'timestamp': 1,
                'data': {'total': 90, 'detalle': [{'concepto': 'multa', 'valor': 90}]}, 'meta': {}}


@tagged('post_install', '-at_install', 'datacil')
class TestHrEmployeeDatacil(DatacilTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'Andrea', 'identification_id': '1710034065'})

    def test_identity_fills_only_empty_fields(self):
        self.employee.private_email = 'keep@example.com'
        with self.mock_get([self.ok(CEDULA_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self.employee.datacil_check_identity()
        self.assertTrue(result['success'], result)
        self.assertTrue(result['reload'])
        self.assertEqual(str(self.employee.birthday), '1990-05-15')
        self.assertEqual(self.employee.gender, 'female')
        self.assertEqual(self.employee.private_email, 'keep@example.com', "Existing data must not be overwritten")
        self.assertEqual(self.employee.private_phone, '0991234567')
        self.assertEqual(self.employee.private_country_id, self.env.ref('base.ec'))
        self.assertEqual(self.employee.country_id, self.env.ref('base.ec'), "Nationality")
        self.assertEqual(self.employee.private_street, 'AV. 9 DE OCTUBRE 123')
        self.assertEqual(self.employee.private_city, 'GUAYAQUIL')
        if 'legal_name' in self.employee._fields:
            self.assertEqual(self.employee.legal_name, 'MARTINEZ SILVA ANDREA LUCIA')
        self.assertEqual(self.employee.identification_id, '1710034065')
        guayas = self.env['res.country.state'].search(
            [('country_id', '=', self.env.ref('base.ec').id), ('name', 'ilike', 'guayas')], limit=1)
        if guayas:
            self.assertEqual(self.employee.private_state_id, guayas)
        self.assertIn('identity', self.employee.datacil_sections)
        self.assertIn('MARTINEZ SILVA', self.employee.datacil_info)
        note = self.employee.message_ids.filtered(lambda m: 'Datacil' in (m.body or ''))
        self.assertTrue(note, "A chatter note must be logged")

    def test_licence(self):
        with self.mock_get([self.ok(LICENCE_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self.employee.datacil_check_licence()
        self.assertTrue(result['success'])
        self.assertTrue(self.employee.datacil_has_licence)
        self.assertEqual(self.employee.datacil_licence_type, 'B', "The active licence wins")
        self.assertEqual(str(self.employee.datacil_licence_valid_until), '2029-12-02')
        self.assertEqual(self.employee.datacil_licence_points, 27.5)
        self.assertEqual(self.employee.datacil_licence_points_max, 30)
        self.assertEqual(str(self.employee.datacil_licence_valid_from), '2024-12-03')
        self.assertFalse(self.employee.datacil_licence_expired)
        self.assertIn('27.5/30', str(result['rows']))
        # Not found is a valid answer: stored as "no licence" instead of an error screen.
        with self.mock_get([self.error(404, 'Licence not found for this cedula')]):
            result = self.employee.datacil_check_licence()
        self.assertTrue(result['success'])
        self.assertFalse(self.employee.datacil_has_licence)
        self.assertFalse(self.employee.datacil_licence_valid_from)

    def test_expired_licence_is_flagged(self):
        payload = {'status': 200, 'success': True, 'message': 'ok', 'timestamp': 1, 'data': {
            'id': '1710034065', 'hasLicence': True,
            'licences': [{'type': 'B', 'validFrom': '2010-01-01', 'validUntil': '2015-01-01', 'isActive': False}],
            'points': {'current': 0, 'max': 30}}, 'meta': {}}
        with self.mock_get([self.ok(payload), self.ok(CREDITS_PAYLOAD)]):
            self.employee.datacil_check_licence()
        self.assertEqual(str(self.employee.datacil_licence_valid_until), '2015-01-01')
        self.assertTrue(self.employee.datacil_licence_expired)

    def test_judicial_and_ant(self):
        with self.mock_get([self.ok(JUDICIAL_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self.employee.datacil_check_judicial()
        self.assertTrue(result['success'])
        self.assertEqual(self.employee.datacil_judicial_count, 1)
        self.assertIn('17230-2024-00001', self.employee.datacil_info)

        with self.mock_get([self.ok(CITATIONS_PAYLOAD), self.ok(CREDITS_PAYLOAD), self.ok(DEBT_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self.employee.datacil_check_ant()
        self.assertTrue(result['success'])
        self.assertEqual(self.employee.datacil_ant_citations, 2)
        self.assertIn('90', str(result['rows']))
        self.assertEqual(set(self.employee.datacil_sections), {'judicial', 'ant'})

    def test_errors_are_forwarded_and_nothing_stored(self):
        with self.mock_get([self.error(402, 'no credits')]):
            result = self.employee.datacil_check_judicial()
        self.assertEqual(result['code'], 'no_credits')
        self.assertFalse(self.employee.datacil_sections)
        self.config.api_key = False
        self.assertEqual(self.employee.datacil_check_licence()['code'], 'not_configured')
