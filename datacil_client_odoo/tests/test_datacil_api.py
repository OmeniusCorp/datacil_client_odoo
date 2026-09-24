from odoo.tests import tagged

from .common import (
    CEDULA_PAYLOAD, COSTS_PAYLOAD, CREDITS_PAYLOAD, HISTORY_PAYLOAD, RUC_PAYLOAD, DatacilTestCommon,
)


@tagged('post_install', '-at_install', 'datacil')
class TestDatacilApi(DatacilTestCommon):

    def test_identification_helpers(self):
        self.assertEqual(self.api.normalize_identification(' 171-003 4065 '), '1710034065')
        self.assertEqual(self.api.identification_kind('1710034065'), 'cedula')
        self.assertEqual(self.api.identification_kind('1790016919001'), 'ruc')
        self.assertFalse(self.api.identification_kind('12345'))
        self.assertFalse(self.api.identification_kind(False))

    def test_not_configured(self):
        self.config.api_key = False
        with self.mock_get([self.ok(CEDULA_PAYLOAD)]) as calls:
            result = self.api.lookup_identification('1710034065')
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 'not_configured')
        self.assertFalse(calls, "No HTTP call must be made without an API key")
        self.assertFalse(self.api.is_configured())

    def test_invalid_length_is_local(self):
        with self.mock_get([self.ok(CEDULA_PAYLOAD)]) as calls:
            result = self.api.lookup_identification('123')
        self.assertEqual(result['code'], 'invalid')
        self.assertFalse(calls)

    def test_lookup_cedula_builds_url_and_headers(self):
        with self.mock_get([self.ok(CEDULA_PAYLOAD), self.ok(CREDITS_PAYLOAD)]) as calls:
            result = self.api.lookup_identification('1710034065')
        self.assertTrue(result['success'])
        self.assertEqual(result['kind'], 'cedula')
        self.assertEqual(result['data']['name'], 'MARTINEZ SILVA ANDREA LUCIA')
        url, kwargs = calls[0]
        self.assertEqual(url, 'https://api-test.datacil.com/v1/ecuador/data/cedula/1710034065')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer sk_test')
        self.assertEqual(kwargs['timeout'], 5)
        # A paid query refreshes the credit balance afterwards.
        self.assertEqual(calls[1][0], 'https://api-test.datacil.com/v1/usage/credits/')
        self.assertEqual(self.config.credits_balance, 120)

    def test_lookup_ruc_url(self):
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]) as calls:
            result = self.api.lookup_identification('1790016919001')
        self.assertTrue(result['success'])
        self.assertEqual(result['kind'], 'ruc')
        self.assertTrue(calls[0][0].endswith('/ecuador/data/ruc/1790016919001'))

    def test_error_mapping(self):
        cases = [
            (self.error(400, 'Cedula invalid'), 'invalid'),
            (self.error(401, 'Not authorized'), 'unauthorized'),
            (self.error(402, 'Payment required'), 'no_credits'),
            (self.error(403, 'Insufficient credits'), 'no_credits'),
            (self.error(403, 'Contract required'), 'forbidden'),
            (self.error(404, 'Not found'), 'not_found'),
            (self.error(429, 'Limite del tier'), 'rate_limit'),
            (self.error(500, 'Internal'), 'unavailable'),
            (self.error(503, 'Down'), 'unavailable'),
            (self.timeout(), 'unavailable'),
            (self.connection_error(), 'unavailable'),
        ]
        for response, expected in cases:
            with self.subTest(expected=expected):
                with self.mock_get([response]):
                    result = self.api.lookup_identification('1710034065')
                self.assertFalse(result['success'])
                self.assertEqual(result['code'], expected)
                self.assertTrue(result['message'])

    def test_no_credits_invalidates_cache(self):
        with self.mock_get([self.ok(CREDITS_PAYLOAD)]):
            self.api.get_credits(force=True)
        self.assertTrue(self.config.credits_synced_at)
        with self.mock_get([self.error(402, 'no credits')]):
            self.api.lookup_identification('1710034065')
        self.assertFalse(self.config.credits_synced_at)

    def test_non_json_body(self):
        with self.mock_get([self.ok(None)]):
            result = self.api.lookup_identification('1710034065')
        # 200 without a body is treated as an empty success payload.
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], {})

    def test_credits_cache(self):
        with self.mock_get([self.ok(CREDITS_PAYLOAD)]) as calls:
            first = self.api.get_credits()
            second = self.api.get_credits()
        self.assertEqual(len(calls), 1, "Second call must be served from cache")
        self.assertFalse(first['data']['cached'])
        self.assertTrue(second['data']['cached'])
        self.assertEqual(second['data']['balance'], 120)
        with self.mock_get([self.ok(dict(CREDITS_PAYLOAD, data={'balance': 90}))]) as calls:
            forced = self.api.get_credits(force=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(forced['data']['balance'], 90)
        self.assertEqual(self.config.credits_balance, 90)

    def test_costs_cache_and_history(self):
        self.api.clear_costs_cache()
        with self.mock_get([self.ok(COSTS_PAYLOAD)]) as calls:
            self.api.get_costs()
            costs = self.api.get_costs()
        self.assertEqual(len(calls), 1)
        self.assertEqual(costs['data']['costs'][0]['serviceKey'], 'ec.cedula')
        # Failures are not cached.
        self.api.clear_costs_cache()
        with self.mock_get([self.error(500), self.ok(COSTS_PAYLOAD)]) as calls:
            self.assertFalse(self.api.get_costs()['success'])
            self.assertTrue(self.api.get_costs()['success'])
        self.assertEqual(len(calls), 2)
        with self.mock_get([self.ok(HISTORY_PAYLOAD)]) as calls:
            history = self.api.get_credits_history(limit=500, offset=10)
        self.assertEqual(calls[0][1]['params'], {'limit': 50, 'offset': 10})
        self.assertEqual(history['data']['transactions'][0]['amount'], -8)

    def test_other_endpoints_urls(self):
        expected = {
            lambda: self.api.get_name('1710034065'): '/ecuador/data/name/1710034065',
            lambda: self.api.autocomplete_companies('comercial'): '/ecuador/data/empresas/autocompletar',
            lambda: self.api.get_licence('1710034065'): '/ecuador/data/licence/1710034065',
            lambda: self.api.get_vehicle('abc-1234'): '/ecuador/data/vehiculo/ABC1234',
            lambda: self.api.get_judicial_cases('1710034065'): '/ecuador/judicial/causas-by-cedula/1710034065',
            lambda: self.api.get_ant_citations('1710034065'): '/ecuador/ant/citaciones/1710034065',
            lambda: self.api.get_ant_points('1710034065'): '/ecuador/ant/puntos/1710034065',
            lambda: self.api.get_ant_debt('1710034065'): '/ecuador/ant/deuda/1710034065',
            lambda: self.api.get_company_risk('1790016919001'): '/ecuador/company/1790016919001/risk',
        }
        payload = {'status': 200, 'success': True, 'message': 'ok', 'timestamp': 1, 'data': {'x': 1}, 'meta': {'credits': 50}}
        for call, suffix in expected.items():
            with self.subTest(suffix=suffix):
                with self.mock_get([self.ok(payload)]) as calls:
                    result = call()
                self.assertTrue(result['success'])
                self.assertTrue(calls[0][0].endswith(suffix), calls[0][0])
        # Balance provided in meta is used instead of an extra HTTP call.
        self.assertEqual(self.config.credits_balance, 50)
        self.assertEqual(self.api.get_vehicle('12')['code'], 'invalid')
        self.assertFalse(self.api.autocomplete_companies('ab')['data'])

    def test_loose_payload_helpers(self):
        api = self.api
        self.assertEqual(api.as_list([1, 2]), [1, 2])
        self.assertEqual(api.as_list({'items': [1]}, 'items'), [1])
        self.assertEqual(api.as_list({'causas': [1, 2]}), [1, 2], "Falls back to the first list")
        self.assertEqual(api.as_list({'total': 2}), [])
        self.assertEqual(api.as_list('nope'), [])

        self.assertEqual(api.as_count([1, 2, 3]), 3)
        self.assertEqual(api.as_count({'total': 5, 'items': [1]}), 5, "A counter wins over a partial list")
        self.assertEqual(api.as_count({'items': [1, 2]}, 'items'), 2)
        self.assertEqual(api.as_count('4'), 4)
        self.assertEqual(api.as_count(None), 0)
        self.assertEqual(api.as_count({'estado': 'ok'}), 0)

        self.assertEqual(api.as_amount(12.5), 12.5)
        self.assertEqual(api.as_amount('1,234.50'), 1234.5)
        self.assertEqual(api.as_amount('1.234,50'), 1234.5)
        self.assertEqual(api.as_amount('$ 45,00'), 45.0)
        self.assertEqual(api.as_amount('1,234'), 1234.0, "A 3 digit group is a thousands separator")
        self.assertEqual(api.as_amount({'valorTotal': '78,50'}), 78.5)
        self.assertEqual(api.as_amount([{'valor': 10}, {'valor': 5}]), 15)
        self.assertEqual(api.as_amount({'estado': 'ok'}), 0.0)
        self.assertEqual(api.as_amount(None), 0.0)

        self.assertEqual(api.as_text({'nombre': 'TOYOTA'}), 'TOYOTA')
        self.assertEqual(api.as_text(['A', 'B']), 'A, B')
        self.assertEqual(api.as_text(2015), '2015')
        self.assertEqual(api.as_text({'other': 1}), '')
        self.assertEqual(api.as_text(None), '')

    def test_parse_address(self):
        api = self.api
        labelled = api.parse_address({
            'street': 'Calle: AV. GENERAL ENRIQUEZ Número: S/N Referencia: FRENTE A DANEC',
            'city': 'COTOGCHOA', 'state': 'PICHINCHA'})
        self.assertEqual(labelled['street'], 'AV. GENERAL ENRIQUEZ', "S/N is not a number")
        self.assertEqual(labelled['street2'], 'FRENTE A DANEC')
        self.assertEqual(labelled['city'], 'COTOGCHOA')
        self.assertEqual(labelled['state'], 'PICHINCHA')

        crossing = api.parse_address({'street': 'Calle: AMAZONAS Numero: N24-03 Interseccion: COLON Referencia: EDIF. TORRE'})
        self.assertEqual(crossing['street'], 'AMAZONAS N24-03 y COLON')
        self.assertEqual(crossing['street2'], 'EDIF. TORRE')

        plain = api.parse_address({'street': 'AV. 9 DE OCTUBRE 123'})
        self.assertEqual(plain['street'], 'AV. 9 DE OCTUBRE 123')
        self.assertFalse(plain['street2'])

        # A province/canton/parish path is a location, never a street.
        path = api.parse_address({'completeAddress': 'GUAYAS/GUAYAQUIL/GUAYAQUIL', 'canton': 'GUAYAQUIL'})
        self.assertFalse(path['street'])
        self.assertEqual(path['city'], 'GUAYAQUIL')
        self.assertEqual(api.parse_address(None), {'street': '', 'street2': '', 'city': '', 'state': '', 'zip': ''})

    def test_format_html_escapes(self):
        html = self.api.format_html({'name': '<b>x</b>', 'items': [{'isActive': True}], 'n': None}, title='T<')
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)
        self.assertIn('T&lt;', html)
        self.assertIn('Is Active', html)
        self.assertNotIn('<b>x</b>', html)
