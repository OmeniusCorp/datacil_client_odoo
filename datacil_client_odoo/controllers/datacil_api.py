from odoo import http, _
from odoo.http import request

GROUP_DASHBOARD = 'datacil_client_odoo.group_access_datacil'


def _denied():
    return {'success': False, 'code': 'forbidden', 'message': _('You are not allowed to access the Datacil dashboard.')}


class DatacilApiController(http.Controller):
    """JSON endpoints used by the Datacil dashboard (backend client action)."""

    @http.route('/datacil/dashboard', type='jsonrpc', auth='user')
    def get_dashboard(self, force=False, limit=50, offset=0):
        """Everything the dashboard needs in a single round trip."""
        if not request.env.user.has_group(GROUP_DASHBOARD):
            return _denied()
        api = request.env['datacil.api']
        credits = api.get_credits(force=force)
        if not credits['success']:
            return {'success': False, 'code': credits['code'], 'message': credits['message']}
        history = api.get_credits_history(limit=limit, offset=offset)
        costs = api.get_costs()
        return {
            'success': True,
            'credits': credits['data'],
            'history': (history['data'] or {}).get('transactions', []) if history['success'] else [],
            'history_error': '' if history['success'] else history['message'],
            'costs': (costs['data'] or {}).get('costs', []) if costs['success'] else [],
        }

    # Kept for backward compatibility with integrations calling the old routes.
    @http.route('/datacil/credits', type='jsonrpc', auth='user')
    def get_credits(self, force=False):
        if not request.env.user.has_group(GROUP_DASHBOARD):
            return _denied()
        return request.env['datacil.api'].get_credits(force=force)

    @http.route('/datacil/credits/history', type='jsonrpc', auth='user')
    def get_credits_history(self, limit=50, offset=0):
        if not request.env.user.has_group(GROUP_DASHBOARD):
            return _denied()
        return request.env['datacil.api'].get_credits_history(limit=limit, offset=offset)

    @http.route('/datacil/costs', type='jsonrpc', auth='user')
    def get_costs(self):
        if not request.env.user.has_group(GROUP_DASHBOARD):
            return _denied()
        return request.env['datacil.api'].get_costs()
