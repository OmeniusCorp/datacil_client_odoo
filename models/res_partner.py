import requests, logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

log = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    button = fields.Boolean('Validate', store=False)
    identification_validated = fields.Boolean(string='Validated Identification', default=False, store=False)

    @api.onchange('button')
    def get_data_identification(self):
        if self.button:
            if not self.vat:
                self.button = False
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _('You must enter an identification number before validating.')
                    }
                }

            validation_service = self.env['datacil.config']
            result = validation_service.validate_identification(self.vat)

            if not result.get('success'):
                self.button = False
                return {
                    'warning': {
                        'title': _('Validation Error'),
                        'message': result.get('message', _('Unknown error during validation.'))
                    }
                }

            data = result.get('data', {})
            if data.get('name'):
                self.name = data['name']
            if data.get('street'):
                self.street = data['street']
            if data.get('city'):
                self.city = data['city']
            if data.get('email'):
                self.email = data['email']
            if data.get('phone'):
                self.phone = data['phone']
            if data.get('cellphone'):
                self.phone = data['cellphone']
            if data.get('state_id'):
                self.state_id = data['state_id']
            if data.get('country_id'):
                self.country_id = data['country_id']

            self.button = False
            return {
                'warning': {
                    'title': _('Validation Successful'),
                    'message': result.get('message')
                }
            }
