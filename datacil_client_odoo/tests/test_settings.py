from odoo.tests import tagged

from .common import CREDITS_PAYLOAD, DatacilTestCommon


@tagged('post_install', '-at_install', 'datacil')
class TestDatacilSettings(DatacilTestCommon):

    def test_settings_roundtrip(self):
        Settings = self.env['res.config.settings']
        settings = Settings.create({})
        self.assertEqual(settings.datacil_api_url, 'https://api-test.datacil.com')
        self.assertEqual(settings.datacil_api_key, 'sk_test')
        self.assertTrue(settings.datacil_is_configured)
        settings.write({'datacil_api_key': 'sk_other', 'datacil_api_delay': 20, 'datacil_load_created_partners': False})
        settings.execute()
        self.assertEqual(self.config.api_key, 'sk_other')
        self.assertEqual(self.config.api_delay, 20)
        self.assertFalse(self.config.load_created_partners)

    def test_settings_without_config_record(self):
        self.config.unlink()
        settings = self.env['res.config.settings'].create({})
        self.assertFalse(settings.datacil_is_configured)
        self.assertEqual(settings.datacil_credits_balance, 0)
        settings.write({'datacil_api_key': 'sk_new', 'datacil_api_url': 'https://api.datacil.com',
                        'datacil_api_version': 'v1', 'datacil_api_country': 'ecuador', 'datacil_api_delay': 10})
        settings.execute()
        config = self.env['datacil.config']._get_for_company()
        self.assertTrue(config)
        self.assertEqual(config.api_key, 'sk_new')

    def test_refresh_credits_button(self):
        settings = self.env['res.config.settings'].create({})
        with self.mock_get([self.ok(CREDITS_PAYLOAD)]):
            action = settings.action_datacil_refresh_credits()
        self.assertEqual(action['params']['type'], 'success')
        self.assertEqual(self.config.credits_balance, 120)
        with self.mock_get([self.error(401, 'Not authorized')]):
            action = settings.action_datacil_refresh_credits()
        self.assertEqual(action['params']['type'], 'danger')

    def test_dashboard_action(self):
        settings = self.env['res.config.settings'].create({})
        action = settings.action_datacil_open_dashboard()
        self.assertEqual(action['tag'], 'datacil_client_odoo.datacil_dashboard')
