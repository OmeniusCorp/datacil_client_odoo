from odoo.tests import tagged

from odoo.addons.datacil_client_odoo.tests.common import CREDITS_PAYLOAD, RUC_PAYLOAD, DatacilTestCommon


@tagged('post_install', '-at_install', 'datacil')
class TestRepairOrderDatacil(DatacilTestCommon):

    def test_partner_warning_and_check(self):
        self.free_vat('1790016919001')
        partner = self.env['res.partner'].create({'name': 'Vendor', 'vat': '1790016919001', 'is_company': True})
        order = self.env['repair.order'].create({'partner_id': partner.id})
        self.assertFalse(order.datacil_partner_warning)
        self.assertEqual(order.datacil_partner_vat, '1790016919001')

        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = order.datacil_check_partner('1790016919001')
        self.assertTrue(result['success'], result)
        self.assertTrue(result['reload'])
        self.assertEqual(result['values'], {}, "Values are written server side, nothing to apply client side")
        self.assertEqual(partner.datacil_ruc_status, 'suspended')
        # Wording depends on the user language: assert the state, not the text.
        self.assertTrue(order.datacil_partner_warning)

    def test_check_on_unsaved_document_uses_identification(self):
        self.free_vat('1790016919001', '0000000000')
        partner = self.env['res.partner'].create({'name': 'Vendor', 'vat': '1790016919001'})
        with self.mock_get([self.ok(RUC_PAYLOAD), self.ok(CREDITS_PAYLOAD)]):
            result = self.env['repair.order'].datacil_check_partner('1790016919001')
        self.assertTrue(result['success'])
        self.assertEqual(partner.datacil_regime, 'general')
        self.assertEqual(self.env['repair.order'].datacil_check_partner('0000000000')['code'], 'invalid')

    def test_check_errors_forwarded(self):
        self.free_vat('1790016919001')
        partner = self.env['res.partner'].create({'name': 'Vendor', 'vat': '1790016919001'})
        order = self.env['repair.order'].create({'partner_id': partner.id})
        with self.mock_get([self.error(503, 'down')]):
            self.assertEqual(order.datacil_check_partner()['code'], 'unavailable')
        self.assertFalse(partner.datacil_last_sync)
