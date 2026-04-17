import requests
from odoo import http, _
from odoo.http import request


class DatacilApiController(http.Controller):

    def _get_config(self):
        config = request.env['datacil.config'].sudo().search([
            ('company', '=', request.env.company.id)
        ], limit=1)
        if self._val_config(config):
            return None, {'success': False, 'message': _('The connection to Datacil has not been configured. Please go to Settings -> Datacil.')}
        return config, None
    
    def _val_config(self, config):
        return not config.api_url or not config.api_key or not config.api_country or not config.api_version

    def _api_get(self, config, path):
        headers = {"Authorization": f"Bearer {config.api_key}"}
        url = f"{config.api_url}/{config.api_version}/{path}"
        response = requests.get(url, headers=headers, timeout=config.api_delay or 10)
        response.raise_for_status()
        return response.json()

    @http.route('/datacil/credits', type='json', auth='user')
    def get_credits(self):
        config, error = self._get_config()
        if error:
            return error
        try:
            result = self._api_get(config, 'usage/credits')
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/datacil/credits/history', type='json', auth='user')
    def get_credits_history(self):
        config, error = self._get_config()
        if error:
            return error
        try:
            result = self._api_get(config, 'usage/credits/history')
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/datacil/costs', type='json', auth='user')
    def get_costs(self):
        config, error = self._get_config()
        if error:
            return error
        try:
            result = self._api_get(config, 'usage/costs')
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            return {'success': False, 'message': str(e)}
