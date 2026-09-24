from odoo import http, _
from odoo.http import request

# Maximum number of lookups per visitor session: keeps a bot from draining credits.
SESSION_LOOKUP_LIMIT = 20


class DatacilWebsiteController(http.Controller):

    @http.route('/datacil/website/lookup', type='json', auth='public', website=True)
    def lookup(self, identification):
        """Return public-safe values for the address form (never exposes other partners)."""
        website = request.website
        if not website.datacil_autocomplete:
            return {'success': False, 'code': 'disabled', 'message': _('Autocomplete is disabled.')}

        api = request.env['datacil.api'].sudo()
        identification = api.normalize_identification(identification)
        if not api.identification_kind(identification):
            return {'success': False, 'code': 'invalid', 'message': _('Enter a 10 digit cédula or a 13 digit RUC.')}

        count = request.session.get('datacil_lookups', 0)
        if count >= SESSION_LOOKUP_LIMIT:
            return {'success': False, 'code': 'rate_limit', 'message': _('Too many queries, please fill the form manually.')}
        request.session['datacil_lookups'] = count + 1

        company = website.company_id
        if website.datacil_autocomplete_mode == 'full':
            result = api.lookup_identification(identification, company=company)
            if not result['success']:
                return {'success': False, 'code': result['code'], 'message': result['message']}
            data = result['data'] or {}
            contact = data.get('contact') or {}
            profile = data.get('profile') or {}
            country = request.env.ref('base.ec', raise_if_not_found=False)
            address = api.parse_address(data.get('address'))
            state = request.env['res.partner'].sudo()._datacil_find_state(address['state'], country)
            values = {
                'name': api.as_text(data.get('name')),
                'street': address['street'],
                'street2': address['street2'],
                'city': address['city'],
                'zip': address['zip'],
                'state_id': state.id if state else False,
                'country_id': country.id if country else False,
                'phone': api.as_text(contact.get('cellphone') or contact.get('phone')),
                'email': api.as_text(contact.get('email')).lower(),
            }
            if profile.get('type') in ('company', 'public_entity'):
                # The checkout keeps the legal name in its own input.
                values['company_name'] = values['name']
        else:
            result = api.get_name(identification, company=company)
            if not result['success']:
                return {'success': False, 'code': result['code'], 'message': result['message']}
            data = result['data'] if isinstance(result['data'], dict) else {}
            values = {'name': api.pick(data, 'name', 'nombre', 'razonSocial', 'razon_social')}

        return {'success': True, 'values': {key: value for key, value in values.items() if value}}
