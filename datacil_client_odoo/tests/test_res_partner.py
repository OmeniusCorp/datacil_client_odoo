from odoo.tests import tagged

from .common import CEDULA_PAYLOAD, CREDITS_PAYLOAD, RUC_PAYLOAD, DatacilTestCommon


@tagged('post_install', '-at_install', 'datacil')
class TestResPartnerLookup(DatacilTestCommon):

    def test_lookup_cedula_values(self):
        Partner = self.env['res.partner']
        self.free_vat('1710034065')
        with self.mock_get([self.ok(CEDULA_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = Partner.datacil_lookup('1710034065')
        self.assertTrue(result['success'], result)
        values = result['values']
        self.assertEqual(values['name'], 'MARTINEZ SILVA ANDREA LUCIA')
        self.assertEqual(values['vat'], '1710034065')
        self.assertEqual(values['street'], 'AV. 9 DE OCTUBRE 123')
        self.assertNotIn('street2', values, "Nothing to put in the second line here")
        self.assertEqual(values['city'], 'GUAYAQUIL')
        self.assertEqual(values['email'], 'andrea@example.com')
        self.assertEqual(values['phone'], '0991234567', "Mobile number wins over landline")
        ecuador = self.env.ref('base.ec')
        self.assertEqual(values['country_id']['id'], ecuador.id)
        guayas = self.env['res.country.state'].search([('country_id', '=', ecuador.id), ('name', 'ilike', 'guayas')], limit=1)
        if guayas:
            self.assertEqual(values['state_id']['id'], guayas.id)
        self.assertEqual(values['datacil_kind'], 'cedula')
        # Datetimes travel as strings in the server format; the widget turns
        # them back into luxon objects before feeding record.update().
        self.assertRegex(values['datacil_last_sync'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
        self.assertNotIn('company_type', values)
        self.assertTrue(any(row['label'] and row['value'] for row in result['rows']))
        self.assertEqual(result['credits']['balance'], 120)
        self.assertFalse(result['warning'])
        if 'l10n_latam_identification_type_id' in Partner._fields and self.env.ref('l10n_ec.ec_dni', raise_if_not_found=False):
            self.assertEqual(values['l10n_latam_identification_type_id']['id'], self.env.ref('l10n_ec.ec_dni').id)

    def test_lookup_ruc_values_and_warning(self):
        Partner = self.env['res.partner']
        self.free_vat('1790016919001')
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = Partner.datacil_lookup('1790016919001')
        values = result['values']
        self.assertEqual(values['company_type'], 'company')
        self.assertEqual(values['datacil_ruc_status'], 'suspended')
        self.assertEqual(values['datacil_regime'], 'general')
        self.assertEqual(values['datacil_profile_type'], 'company')
        self.assertEqual(values['datacil_activity'], 'COMERCIO AL POR MAYOR')
        # The SRI street comes labelled: way and number on street, reference on street2.
        self.assertEqual(values['street'], 'AV. PRINCIPAL S24-456 y CALLE SECUNDARIA')
        self.assertEqual(values['street2'], 'FRENTE AL PARQUE')
        self.assertEqual(values['city'], 'QUITO')
        self.assertTrue(values['datacil_special_contributor'])
        self.assertEqual(values['phone'], '022345678')
        # Server-side enrichment writes the same values and computes the warning.
        partner = Partner.create({'name': 'tmp', 'vat': '1790016919001'})
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            partner.datacil_enrich()
        self.assertEqual(partner.name, 'DISTRIBUIDORA COMERCIAL DEL PACIFICO S.A.')
        self.assertTrue(partner.is_company)
        self.assertEqual(partner.datacil_ruc_status, 'suspended')
        # Wording depends on the user language: assert the state, not the text.
        self.assertTrue(partner.datacil_warning)
        self.assertTrue(partner.datacil_last_sync)

    def test_lookup_errors_are_forwarded(self):
        Partner = self.env['res.partner']
        self.assertEqual(Partner.datacil_lookup('')['code'], 'invalid')
        self.assertEqual(Partner.datacil_lookup('12')['code'], 'invalid')
        with self.mock_get([self.error(404, 'Not found')]):
            self.assertEqual(Partner.datacil_lookup('1710034065')['code'], 'not_found')
        with self.mock_get([self.timeout()]):
            self.assertEqual(Partner.datacil_lookup('1710034065')['code'], 'unavailable')
        self.config.api_key = False
        self.assertEqual(Partner.datacil_lookup('1710034065')['code'], 'not_configured')

    def test_already_registered(self):
        Partner = self.env['res.partner']
        self.free_vat('1710034065')
        existing = Partner.create({'name': 'Existing', 'vat': '1710034065'})
        self.config.load_created_partners = False
        with self.mock_get([self.ok(CEDULA_PAYLOAD)]) as calls:
            result = Partner.datacil_lookup('1710034065')
        self.assertEqual(result['code'], 'already_exists')
        self.assertEqual(result['existing_partner']['id'], existing.id)
        self.assertFalse(calls, "No credits must be spent when loading registered partners is disabled")
        self.config.load_created_partners = True
        with self.mock_get([self.ok(CEDULA_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = Partner.datacil_lookup('1710034065')
        self.assertTrue(result['success'])
        self.assertIn('Existing', result['warning'])
        self.assertEqual(result['existing_partner']['id'], existing.id)

    def test_enrich_raises_on_error(self):
        partner = self.env['res.partner'].create({'name': 'tmp', 'vat': '1710034065'})
        with self.mock_get([self.error(500)]):
            with self.assertRaises(Exception):
                partner.datacil_enrich()
