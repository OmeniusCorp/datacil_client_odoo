import logging
import re

from markupsafe import Markup

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# SRI / ANT wording mapped to the native fleet selections.
FUEL_TYPES = {
    'gasolina': 'gasoline', 'gasoline': 'gasoline', 'extra': 'gasoline', 'super': 'gasoline', 'ecopais': 'gasoline',
    'diesel': 'diesel', 'diésel': 'diesel',
    'electrico': 'electric', 'eléctrico': 'electric', 'electric': 'electric',
    'hibrido': 'full_hybrid', 'híbrido': 'full_hybrid', 'hybrid': 'full_hybrid',
    'gas': 'lpg', 'glp': 'lpg', 'gnc': 'cng', 'gnv': 'cng', 'hidrogeno': 'hydrogen', 'hidrógeno': 'hydrogen',
}
TRANSMISSIONS = {
    'manual': 'manual', 'mecanica': 'manual', 'mecánica': 'manual', 'estandar': 'manual', 'estándar': 'manual',
    'automatica': 'automatic', 'automática': 'automatic', 'automatico': 'automatic', 'automático': 'automatic',
    'automatic': 'automatic', 'cvt': 'automatic', 'tiptronic': 'automatic',
}
# Two wheels are bikes in the fleet catalog, everything else is a car.
BIKE_WORDS = ('motocicleta', 'moto', 'bicicleta', 'tricimoto', 'cuadron', 'cuadrón')


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    datacil_last_sync = fields.Datetime(string="Datacil Last Query", readonly=True, copy=False)
    datacil_owner_vat = fields.Char(string="Registered Owner ID", readonly=True, copy=False)
    datacil_owner_name = fields.Char(string="Registered Owner", readonly=True, copy=False)
    datacil_service_type = fields.Char(string="Service Type (ANT)", readonly=True, copy=False)
    datacil_vehicle_class = fields.Char(string="Vehicle Class (ANT)", readonly=True, copy=False)
    datacil_last_registration = fields.Char(string="Last Registration (ANT)", readonly=True, copy=False)
    datacil_pending_fees = fields.Float(string="Pending Fees (ANT)", readonly=True, copy=False)
    datacil_citation_count = fields.Integer(string="Citations (ANT)", readonly=True, copy=False)
    datacil_info = fields.Html(string="Datacil Information", readonly=True, copy=False, sanitize=False)

    def datacil_lookup_vehicle(self, plate=None):
        """Widget entry point: query the plate and return values for the form."""
        api_model = self.env['datacil.api']
        plate = plate or (self[:1].license_plate if self else '')
        result = api_model.get_vehicle(plate)
        if not result['success']:
            return result

        data = result['data'] or {}
        plate_label = re.sub(r'[^A-Za-z0-9]', '', plate or '').upper()
        info = str(api_model.format_html(data))
        try:
            values, rows = self._datacil_vehicle_values(data, plate_label)
        except Exception:  # noqa: BLE001 - an unexpected payload still shows its data
            _logger.exception("Datacil: unexpected vehicle payload for plate %s", plate_label)
            values, rows = {}, [(_('Plate'), plate_label)]
        values.update({
            'datacil_last_sync': fields.Datetime.now(),
            'datacil_info': info,
        })

        if self:
            self[:1].message_post(
                body=Markup('<p><b>%s</b></p>%s') % (_('Datacil: vehicle %s', plate_label), Markup(info)),
                message_type='comment', subtype_xmlid='mail.mt_note')

        response = api_model._result(True, 'ok', result['message'])
        response.update({
            'title': _('Datacil: vehicle %s', plate_label),
            'values': api_model.to_web_values(self._name, values),
            'rows': [{'label': label, 'value': value} for label, value in rows if value not in (None, '', False)],
            'html': info if not rows[1:] else '',
            'credits': self.env['res.partner']._datacil_credits_info(api_model._get_config()),
        })
        return response

    def _datacil_vehicle_values(self, data, plate_label):
        """Map the vehicle payload to native fleet fields and dialog rows.

        Every block is read defensively: the API documents the endpoint but not
        the shape of each block, and a block that could not be fetched comes
        back as ``null`` or as a counter dict instead of a list.
        """
        api_model = self.env['datacil.api']
        vehicle = api_model.pick(data, 'vehiculo', 'vehicle', 'datos', default=data)
        if not isinstance(vehicle, dict):
            vehicle = {}
        owner = api_model.pick(data, 'propietario', 'owner', 'titular', default={}) or {}
        if not isinstance(owner, dict):
            owner = {'nombre': owner}

        def text(*keys, block=vehicle):
            return api_model.as_text(api_model.pick(block, *keys))

        def number(*keys, block=vehicle):
            return api_model.as_amount(api_model.pick(block, *keys))

        citation_count = api_model.as_count(
            api_model.pick(data, 'citaciones', 'citations', 'citacionesCount', 'multas', default=[]),
            'citaciones', 'citations', 'items', 'multas')
        fees = api_model.as_amount(
            api_model.pick(data, 'deuda', 'valoresPendientes', 'pendingFees', 'fees', 'valores', default=0))

        brand_name = text('marca', 'brand', 'make')
        model_name = text('modelo', 'model')
        vehicle_class = text('clase', 'tipo', 'class', 'vehicleClass', 'tipoVehiculo')
        service_type = text('servicio', 'tipoServicio', 'serviceType', 'uso')
        owner_vat = api_model.normalize_identification(
            api_model.as_text(api_model.pick(owner, 'cedula', 'identificacion', 'id', 'ruc')))
        owner_name = api_model.as_text(api_model.pick(owner, 'nombre', 'name', 'razonSocial'))

        values = {
            'license_plate': plate_label,
            'vin_sn': text('chasis', 'chassis', 'vin', 'numeroChasis', 'numeroVin'),
            'color': text('color'),
            'model_year': text('anio', 'año', 'year', 'modelYear', 'anioModelo', 'anioFabricacion'),
            'model_id': self._datacil_find_or_create_model(brand_name, model_name, vehicle_class),
            'fuel_type': self._datacil_map_selection(text('combustible', 'fuel', 'tipoCombustible'), FUEL_TYPES),
            'transmission': self._datacil_map_selection(text('transmision', 'transmisión', 'transmission', 'caja'), TRANSMISSIONS),
            'seats': int(number('asientos', 'pasajeros', 'numeroAsientos', 'seats') or 0),
            'doors': int(number('puertas', 'numeroPuertas', 'doors') or 0),
            'power': number('potencia', 'power', 'kw'),
            'car_value': number('avaluo', 'avalúo', 'valor', 'catalogValue'),
            'acquisition_date': self._datacil_date(text('fechaMatricula', 'fechaRegistro', 'registrationDate', 'fechaCompra')),
            'datacil_owner_vat': owner_vat,
            'datacil_owner_name': owner_name,
            'datacil_vehicle_class': vehicle_class,
            'datacil_service_type': service_type,
            'datacil_last_registration': text('ultimaMatricula', 'anioUltimaMatricula', 'lastRegistration', 'matricula'),
            'datacil_pending_fees': fees,
            'datacil_citation_count': citation_count,
        }
        if owner_vat and not (self and self[:1].driver_id):
            driver = self.env['res.partner']._datacil_find_existing(owner_vat)
            if driver:
                values['driver_id'] = driver.id
        # Keep the model year only when it is a plain year (the field is a Char).
        if not re.fullmatch(r'(19|20)\d{2}', values['model_year'] or ''):
            values['model_year'] = False
        # Never blank a field that the API did not answer for.
        keep_zero = ('datacil_pending_fees', 'datacil_citation_count')
        values = {key: value for key, value in values.items() if value not in (None, '', False, 0, 0.0) or key in keep_zero}

        rows = [
            (_('Plate'), plate_label),
            (_('Brand'), brand_name),
            (_('Model'), model_name),
            (_('Class'), vehicle_class),
            (_('Service type'), service_type),
            (_('Year'), values.get('model_year')),
            (_('Color'), values.get('color')),
            (_('Chassis'), values.get('vin_sn')),
            (_('Fuel'), dict(self._fields['fuel_type']._description_selection(self.env)).get(values.get('fuel_type'))),
            (_('Transmission'), dict(self._fields['transmission']._description_selection(self.env)).get(values.get('transmission'))),
            (_('Seats'), values.get('seats')),
            (_('Doors'), values.get('doors')),
            (_('Appraisal'), values.get('car_value')),
            (_('Registration date'), values.get('acquisition_date')),
            (_('Registered owner'), f"{owner_name} ({owner_vat})" if owner_vat else owner_name),
            (_('Pending fees'), fees or None),
            (_('Citations'), citation_count or None),
        ]
        if values.get('driver_id'):
            rows.append((_('Driver'), self.env['res.partner'].browse(values['driver_id']).display_name))
        elif owner_vat:
            rows.append((_('Note'), _('The registered owner is not a contact yet; create it to link it as driver.')))
        return values, rows

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _datacil_map_selection(self, value, mapping):
        """Map free ANT wording ("GASOLINA", "AUTOMATICA") to a native selection."""
        value = (value or '').strip().lower()
        if not value:
            return False
        for word, key in mapping.items():
            if word in value:
                return key
        return False

    @api.model
    def _datacil_date(self, value):
        """Accept ``YYYY-MM-DD``, ``DD/MM/YYYY`` or a bare year."""
        value = (value or '').strip()
        if not value:
            return False
        for pattern, order in ((r'^(\d{4})-(\d{2})-(\d{2})', 'ymd'), (r'^(\d{2})[/-](\d{2})[/-](\d{4})', 'dmy')):
            match = re.match(pattern, value)
            if match:
                year, month, day = match.groups() if order == 'ymd' else match.group(3, 2, 1)
                try:
                    return fields.Date.to_date(f"{year}-{month}-{day}")
                except ValueError:
                    return False
        if re.fullmatch(r'\d{4}', value):
            return fields.Date.to_date(f"{value}-01-01")
        return False

    def _datacil_find_or_create_model(self, brand_name, model_name, vehicle_class=''):
        """Return the catalog model, creating brand and model when missing.

        ``model_id`` is required on a vehicle, so a plate whose model is not in
        the catalog could not be filled at all otherwise.
        """
        if not model_name and not brand_name:
            return False
        Model = self.env['fleet.vehicle.model']
        Brand = self.env['fleet.vehicle.model.brand']
        model_name = (model_name or brand_name).strip()
        brand_name = (brand_name or model_name).strip()

        domain = [('name', '=ilike', model_name), ('brand_id.name', '=ilike', brand_name)]
        model = Model.search(domain, limit=1) or Model.search(
            [('name', 'ilike', model_name), ('brand_id.name', 'ilike', brand_name)], limit=1)
        if model:
            return model.id

        brand = Brand.search([('name', '=ilike', brand_name)], limit=1) or Brand.create({'name': brand_name})
        is_bike = any(word in (vehicle_class or '').lower() for word in BIKE_WORDS)
        model = Model.create({
            'name': model_name,
            'brand_id': brand.id,
            'vehicle_type': 'bike' if is_bike else 'car',
        })
        _logger.info("Datacil: created fleet model %s / %s", brand.name, model.name)
        return model.id
