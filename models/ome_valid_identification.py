from odoo import fields, models
from odoo.exceptions import UserError
import requests

class OmeValidIdentification(models.Model):
    _name = "ome.valid.identification"
    _description = "Configuracion de Validacion de Identificacion"
    _rec_name = "company"

    company = fields.Many2one(
        "res.company",
        string="Compañia", 
        required=True,
        ondelete="cascade", 
        default=lambda self: self.env.company,
    )
    api_url = fields.Char(string="URL", default='https://api.datacil.com', required=False)
    api_key = fields.Char(string="API Key", required=False)
    api_delay = fields.Float(string="Tiempo de respuesta", default=0.0)
    api_version = fields.Selection(
        selection=[('v1', 'Version 1')],
        string='API Version',
        default='v1'
    )
    api_country = fields.Selection(
        selection=[('ecuador', 'Ecuador')],
        string='API Country',
        default='ecuador'
    )

    load_created_partners = fields.Boolean(string="Permitir cargar clientes ya registrados", default=False)

    def validate_identification(self, vat, type):
        valid_types = ["Cédula", "RUC"]

        config = self.env['ome.valid.identification'].search([
            ('company', '=', self.env.company.id)
        ], limit=1)
        if not config:
            raise UserError("No se ha configurado la conexión con el servicio de validación.")

        if type not in valid_types:
            return {
                'success': False,
                'message': f"No se puede validar los datos del tipo de identificacion '{type}'."
            }

        if type == "Cédula" and len(vat) != 10:
            return {
                'success': False,
                'message': "Una Cédula ecuatoriana debe tener exactamente 10 dígitos."
            }

        if type == "RUC" and len(vat) != 13:
            return {
                'success': False,
                'message': "Un RUC ecuatoriano debe tener exactamente 13 dígitos."
            }

        headers = {
            "Authorization": f"Bearer {config.api_key}"
        }

        if not vat:
            return {
                'success': False,
                'message': 'Debe ingresar un número de identificación (Tax ID) antes de validar.'
            }
        
        existing_partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)

        if existing_partner:
            msg = f'El número de identificación {vat} ya se encuentra registrado para: {existing_partner.name}'
            if not config.load_created_partners:
                return {
                    'success': False,
                    'message': msg
                }
            warning_message = msg
        else:
            warning_message = None

        data = {}
        endpoint = None
        base_url = f"{config.api_url}/{config.api_version}/{config.api_country}/data"

        if type == "Cédula":
            endpoint = f"{base_url}/cedula/{vat}"
        elif type == "RUC":
            endpoint = f"{base_url}/ruc/{vat}"

        if endpoint:
            try:
                response = requests.get(endpoint, headers=headers, timeout=config.api_delay)
                if response.status_code == 400:
                    return {
                        'success': False,
                        'message': f'La identificacion ingresada {vat} es invalida para su tipo {type}.'
                    }
                if response.status_code == 404:
                    return {
                        'success': False,
                        'message': f'La identificacion ingresada {vat} no fue encontrada.'
                    }
                if response.status_code == 500:
                    return {
                        'success': False,
                        'message': f'Error en nuestros servicios, por favor intentelo de nuevo en unos minutos.'
                    }
                result = response.json()
                
                data = result.get("data", {})
            except Exception as e:
                return {
                    'success': False,
                    'message': f'No se pudo conectar con el servicio externo: {str(e)}'
                }

            name = data.get("name") or vat.name or ""
            city = data.get("address", {}).get("city") or ""
            street = data.get("address", {}).get("street") or ""
            state = data.get("address", {}).get("state") or ""
            email = data.get("contact", {}).get("email") or ""
            cellphone = data.get("contact", {}).get("cellphone") or ""
            phone = data.get("contact", {}).get("phone") or ""

            country = self.env['res.country'].search([('name', 'ilike', config.api_country)], limit=1)
            
            odoo_state = ''
            if state and country:
                odoo_state = self.env['res.country.state'].search([
                    ('name', 'ilike', state),
                    ('country_id', '=', country.id)
                ], limit=1)

            response = {
                'success': True,
                'message': f'Identificación validada correctamente para {name}',
                'data': {
                    'name': name,
                    'street': street,
                    'city': city,
                    'email': email,
                    'cellphone': cellphone,
                    'phone': phone,
                    'state_id': odoo_state.id if odoo_state else False,
                    'country_id': country.id if country else False,
                    'vat': vat,
                }
            }

            if warning_message:
                response['message'] = f'{warning_message}'

            return response
        else:
            return {
                'success': False,
                'message': f'No se encontro un endpoint para el tipo de identificacion ingresado.'
            }