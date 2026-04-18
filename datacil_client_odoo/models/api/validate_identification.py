from odoo import models, _
from odoo.exceptions import UserError
import requests

class DatacilConfig(models.Model):
    _inherit = 'datacil.config'

    def validate_identification(self, vat):
        config = self.env['datacil.config'].search([
            ('company', '=', self.env.company.id)
        ], limit=1)
        if self._val_config(config):
            raise UserError(_("The connection to the validation service has not been configured for this company. Please go to Settings -> Datacil."))

        if not vat:
            return {
                'success': False,
                'message': _('You must enter an identification number (Tax ID) before validating.')
            }

        if len(vat) != 10 and len(vat) != 13:
            return {
                'success': False,
                'message': _('You must enter a valid number of digits (10 for ID, 13 for RUC).')
            }

        existing_partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)

        if existing_partner:
            msg = _('The identification number %s is already registered for: %s') % (vat, existing_partner.name)
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
                        'message': _('The entered identification %s is invalid for its type.') % vat
                    }
                if response.status_code == 404:
                    return {
                        'success': False,
                        'message': _('The entered identification %s was not found.') % vat
                    }
                if response.status_code == 500:
                    return {
                        'success': False,
                        'message': _('Error in our services, please try again in a few minutes.')
                    }
                result = response.json()

                data = result.get("data", {})
            except Exception as e:
                return {
                    'success': False,
                    'message': _('Could not connect to the external service: %s') % str(e)
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
                'message': _('Identification successfully validated for %s') % name,
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
                response['message'] = warning_message

            return response
        else:
            return {
                'success': False,
                'message': _('No endpoint found for the entered identification type.')
            }

    def _get_enpoint(self, config, vat):
        base_url = f"{config.api_url}/{config.api_version}/{config.api_country}/data"

        if len(vat) == 10:
            return f"{base_url}/cedula/{vat}"
        elif len(vat) == 13:
            return f"{base_url}/ruc/{vat}"

    def _val_config(self, config):
        return not config.api_url or not config.api_key or not config.api_country or not config.api_version