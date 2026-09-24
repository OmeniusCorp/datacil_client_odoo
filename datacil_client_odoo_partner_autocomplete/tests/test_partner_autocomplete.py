from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.datacil_client_odoo.tests.common import CREDITS_PAYLOAD, RUC_PAYLOAD, DatacilTestCommon

NAME_PAYLOAD = {'status': 200, 'success': True, 'message': 'ok', 'timestamp': 1,
                'data': {'id': '1790016919001', 'name': 'DISTRIBUIDORA COMERCIAL DEL PACIFICO S.A.'}, 'meta': {}}
SUGGESTIONS_PAYLOAD = {'status': 200, 'success': True, 'message': 'Sugerencias', 'timestamp': 1,
                       'data': [{'ruc': '1790016919001', 'razonSocial': 'DISTRIBUIDORA COMERCIAL DEL PACIFICO S.A.',
                                 'provincia': 'PICHINCHA', 'actividad': 'COMERCIO'},
                                {'ruc': '', 'razonSocial': 'IGNORED'}],
                       'meta': {}}
IAP_PATH = 'odoo.addons.partner_autocomplete.models.iap_autocomplete_api.IapAutocompleteApi._request_partner_autocomplete'


@tagged('post_install', '-at_install', 'datacil')
class TestPartnerAutocompleteDatacil(DatacilTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ecuador = cls.env.ref('base.ec')
        cls.company.country_id = cls.ecuador

    def test_identification_suggestion_is_free(self):
        Partner = self.env['res.partner']
        with self.mock_get([self.ok(NAME_PAYLOAD)]) as calls, patch(IAP_PATH) as iap:
            suggestions = Partner.autocomplete_by_name('1790016919001', self.ecuador.id)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][0].endswith('/ecuador/data/name/1790016919001'))
        iap.assert_not_called()
        self.assertEqual(suggestions[0]['name'], 'DISTRIBUIDORA COMERCIAL DEL PACIFICO S.A.')
        self.assertEqual(suggestions[0]['datacil_id'], '1790016919001')
        self.assertEqual(suggestions[0]['country_id']['id'], self.ecuador.id)
        with self.mock_get([self.ok(NAME_PAYLOAD)]), patch(IAP_PATH) as iap:
            self.assertEqual(Partner.autocomplete_by_vat('1790016919001', False)[0]['vat'], '1790016919001')
        iap.assert_not_called()

    def test_company_name_suggestions(self):
        with self.mock_get([self.ok(SUGGESTIONS_PAYLOAD)]) as calls:
            suggestions = self.env['res.partner'].autocomplete_by_name('pacifico', self.ecuador.id)
        self.assertEqual(calls[0][1]['params'], {'q': 'pacifico'})
        self.assertEqual(len(suggestions), 1, "Entries without RUC are dropped")
        self.assertEqual(suggestions[0]['city'], 'PICHINCHA')

    def test_other_countries_and_worldwide_use_iap(self):
        belgium = self.env.ref('base.be')
        with self.mock_get([self.ok(SUGGESTIONS_PAYLOAD)]) as calls, patch(IAP_PATH, return_value=(False, 'No account token')) as iap:
            self.assertEqual(self.env['res.partner'].autocomplete_by_name('pacifico', belgium.id), [])
            self.assertEqual(self.env['res.partner'].autocomplete_by_name('pacifico', 0), [])
        self.assertFalse(calls)
        self.assertEqual(iap.call_count, 2)

    def test_not_configured_falls_back_to_iap(self):
        self.config.api_key = False
        with self.mock_get([self.ok(SUGGESTIONS_PAYLOAD)]) as calls, patch(IAP_PATH, return_value=(False, 'No account token')) as iap:
            self.env['res.partner'].autocomplete_by_name('pacifico', self.ecuador.id)
        self.assertFalse(calls)
        iap.assert_called_once()

    def test_enrich_selected_suggestion(self):
        Partner = self.env['res.partner'].with_context(enriched_company_data={'datacil_id': '1790016919001', 'duns': '1790016919001'})
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]), patch(IAP_PATH) as iap:
            values = Partner.enrich_by_duns('1790016919001')
        iap.assert_not_called()
        self.assertEqual(values['name'], 'DISTRIBUIDORA COMERCIAL DEL PACIFICO S.A.')
        self.assertEqual(values['company_type'], 'company')
        self.assertEqual(values['country_id']['id'], self.ecuador.id)
        self.assertEqual(values['datacil_ruc_status'], 'suspended')
        # The native widget pushes these values into record.update(): a datetime
        # string would break it, so dates stay server side.
        self.assertNotIn('datacil_last_sync', values)
        self.assertFalse([name for name, value in values.items() if isinstance(value, str) and name.endswith('_date')])
        with self.mock_get([self.error(402, 'no credits')]):
            error = Partner.enrich_by_duns('1790016919001')
        self.assertTrue(error['error'])
        self.assertEqual(error['error_message'], 'Insufficient Credit')
        # Without the Datacil marker, the native IAP flow is used.
        with patch(IAP_PATH, return_value=(False, 'No account token')) as iap:
            self.env['res.partner'].enrich_by_duns('123456789')
        iap.assert_called_once()

    def test_message_post_uses_datacil_card(self):
        partner = self.env['res.partner'].create({'name': 'tmp', 'vat': '1790016919001'})
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            partner.datacil_enrich()
        partner.enrich_company_message_post({})
        note = partner.message_ids.filtered(lambda m: 'Datacil' in (m.body or ''))
        self.assertTrue(note)
        self.assertIn('COMERCIO AL POR MAYOR', note[0].body)

    def test_autocomplete_flow_stamps_the_query_date(self):
        """Full native flow: suggestion, enrichment applied by the widget, note."""
        Partner = self.env['res.partner']
        with self.mock_get([self.ok(NAME_PAYLOAD)]):
            suggestion = Partner.autocomplete_by_vat('1790016919001', False)[0]
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            values = Partner.with_context(enriched_company_data=suggestion).enrich_by_duns(suggestion['duns'])
        partner = Partner.create({
            'name': values['name'],
            'vat': values['vat'],
            'company_type': values['company_type'],
            'datacil_kind': values['datacil_kind'],
            'datacil_ruc_status': values['datacil_ruc_status'],
            'datacil_activity': values['datacil_activity'],
        })
        self.assertFalse(partner.datacil_last_sync, "The widget cannot carry the datetime")
        partner.enrich_company_message_post({})
        self.assertTrue(partner.datacil_last_sync, "Stamped server side after the save")
        self.assertTrue(partner.message_ids.filtered(lambda m: 'Datacil' in (m.body or '')))

    def test_name_search_without_company_country(self):
        """Datacil answers for Ecuador even if the company country is not set."""
        self.company.country_id = False
        with self.mock_get([self.ok(SUGGESTIONS_PAYLOAD)]) as calls:
            suggestions = self.env['res.partner'].autocomplete_by_name('pacifico', False)
        self.assertTrue(calls, "The Datacil configuration is enough")
        self.assertEqual(len(suggestions), 1)
