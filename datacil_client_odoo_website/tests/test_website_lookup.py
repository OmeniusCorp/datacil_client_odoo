import json

from odoo.tests import HttpCase, tagged

from odoo.addons.datacil_client_odoo.tests.common import CEDULA_PAYLOAD, CREDITS_PAYLOAD, DatacilTestCommon

NAME_PAYLOAD = {'status': 200, 'success': True, 'message': 'ok', 'timestamp': 1,
                'data': {'id': '1710034065', 'name': 'MARTINEZ SILVA ANDREA LUCIA'}, 'meta': {}}


@tagged('post_install', '-at_install', 'datacil')
class TestWebsiteLookup(DatacilTestCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].get_current_website()
        cls.website.write({'datacil_autocomplete': True, 'datacil_autocomplete_mode': 'name'})

    def _lookup(self, identification):
        response = self.url_open(
            '/datacil/website/lookup',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {'identification': identification}}),
            headers={'Content-Type': 'application/json'},
        )
        response.raise_for_status()
        return response.json()['result']

    def test_disabled(self):
        self.website.datacil_autocomplete = False
        with self.mock_get([self.ok(NAME_PAYLOAD)]) as calls:
            result = self._lookup('1710034065')
        self.assertEqual(result['code'], 'disabled')
        self.assertFalse(calls)

    def test_invalid_identification(self):
        with self.mock_get([self.ok(NAME_PAYLOAD)]) as calls:
            result = self._lookup('123')
        self.assertEqual(result['code'], 'invalid')
        self.assertFalse(calls)

    def test_name_mode_uses_free_endpoint(self):
        with self.mock_get([self.ok(NAME_PAYLOAD)]) as calls:
            result = self._lookup('1710034065')
        self.assertTrue(result['success'], result)
        self.assertEqual(result['values'], {'name': 'MARTINEZ SILVA ANDREA LUCIA'})
        self.assertTrue(calls[0][0].endswith('/ecuador/data/name/1710034065'))

    def test_full_mode_never_exposes_partners(self):
        self.website.datacil_autocomplete_mode = 'full'
        self.env['res.partner'].create({'name': 'Secret customer', 'vat': '1710034065'})
        with self.mock_get([self.ok(CEDULA_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self._lookup('1710034065')
        self.assertTrue(result['success'], result)
        values = result['values']
        self.assertEqual(values['name'], 'MARTINEZ SILVA ANDREA LUCIA')
        self.assertEqual(values['street'], 'AV. 9 DE OCTUBRE 123')
        self.assertEqual(values['phone'], '0991234567')
        self.assertEqual(values['country_id'], self.env.ref('base.ec').id)
        self.assertNotIn('existing_partner', result)
        self.assertNotIn('Secret', json.dumps(result))

    def test_api_errors_forwarded(self):
        with self.mock_get([self.error(503, 'down')]):
            result = self._lookup('1710034065')
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 'unavailable')
