from odoo.tests import tagged

from odoo.addons.datacil_client_odoo.tests.common import CEDULA_PAYLOAD, CREDITS_PAYLOAD, RUC_PAYLOAD, DatacilTestCommon


@tagged('post_install', '-at_install', 'datacil')
class TestCrmLeadDatacil(DatacilTestCommon):

    def test_lookup_fills_lead_fields(self):
        Lead = self.env['crm.lead']
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = Lead.datacil_lookup('1790016919001')
        self.assertTrue(result['success'])
        values = result['values']
        self.assertEqual(values['partner_name'], 'DISTRIBUIDORA COMERCIAL DEL PACIFICO S.A.')
        self.assertNotIn('contact_name', values)
        self.assertEqual(values['datacil_vat'], '1790016919001')
        self.assertEqual(values['email_from'], 'info@pacifico.com')
        self.assertEqual(values['country_id']['id'], self.env.ref('base.ec').id)
        self.assertNotIn('datacil_kind', values, "Partner-only fields must not leak into the lead")

        with self.mock_get([self.ok(CEDULA_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = Lead.datacil_lookup('1710034065')
        self.assertEqual(result['values']['contact_name'], 'MARTINEZ SILVA ANDREA LUCIA')

    def test_lookup_links_existing_partner(self):
        self.free_vat('1710034065')
        partner = self.env['res.partner'].create({'name': 'Existing', 'vat': '1710034065'})
        with self.mock_get([self.ok(CEDULA_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self.env['crm.lead'].datacil_lookup('1710034065')
        self.assertEqual(result['values']['partner_id']['id'], partner.id)

    def test_errors_forwarded(self):
        with self.mock_get([self.error(404)]):
            self.assertEqual(self.env['crm.lead'].datacil_lookup('1710034065')['code'], 'not_found')

    def test_vat_carried_to_created_customer(self):
        self.free_vat('1710034065')
        lead = self.env['crm.lead'].create({'name': 'Lead', 'contact_name': 'Andrea', 'datacil_vat': '1710034065'})
        lead._handle_partner_assignment(create_missing=True)
        self.assertEqual(lead.partner_id.vat, '1710034065')

    def test_vat_synced_from_partner(self):
        partner = self.env['res.partner'].create({'name': 'P', 'vat': '1710034065'})
        lead = self.env['crm.lead'].create({'name': 'Lead', 'partner_id': partner.id})
        self.assertEqual(lead.datacil_vat, '1710034065')
