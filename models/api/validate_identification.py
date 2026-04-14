from odoo import models
from odoo.exceptions import UserError
import requests

class DatacilConfig(models.Model):
    _inherit = 'datacil.config'

    def validate_identification(self, vat):
        config = self.env['datacil.config'].search([
            ('company', '=', self.env.company.id)
        ], limit=1)
        if not config:
            raise UserError("No se ha configurado la conexión con el servicio de validación para esta compañia.")

        if not vat:
            return {
                'success': False,
                'message': 'Debe ingresar un número de identificación (Tax ID) antes de validar.'
            }
        
        if len(vat) != 10 and len(vat) != 13:
            return {
                'success': False,
                'message': 'Debe ingresa una cantidad valida de digitos (10 para cedula, 13 para RUC).'
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
        endpoint = self._get_enpoint(config, vat)

        if endpoint:
            try:
                response = requests.get(endpoint, headers={"Authorization": f"Bearer {config.api_key}"}, timeout=config.api_delay)
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

            name = data.get("name") or ""
            state = data.get("address", {}).get("state") or ""
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
                    'street': data.get("address", {}).get("street") or "",
                    'city': data.get("address", {}).get("city") or "",
                    'email': data.get("contact", {}).get("email") or "",
                    'cellphone': data.get("contact", {}).get("cellphone") or "",
                    'phone': data.get("contact", {}).get("phone") or "",
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
    
    def _get_enpoint(self, config, vat):
        base_url = f"{config.api_url}/{config.api_version}/{config.api_country}/data"

        if len(vat) == 10:
            return f"{base_url}/cedula/{vat}"
        elif len(vat) == 13:
            return f"{base_url}/ruc/{vat}"