from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    datacil_config_id = fields.Many2one('datacil.config', compute='_compute_datacil_config_id')
    datacil_api_url = fields.Char(string="API URL")
    datacil_api_key = fields.Char(string="API Key")
    datacil_api_version = fields.Selection(
        selection=[('v1', 'Version 1')],
        string='API Version',
    )
    datacil_api_country = fields.Selection(
        selection=[('ecuador', 'Ecuador')],
        string='API Country',
    )
    datacil_api_delay = fields.Float(string="Maximum Response Time")
    datacil_load_created_partners = fields.Boolean(string="Allow loading already registered customers")

    # Mini dashboard (read-only, served from the cached balance: no HTTP call on page load).
    datacil_is_configured = fields.Boolean(compute='_compute_datacil_credits')
    datacil_credits_balance = fields.Float(compute='_compute_datacil_credits', digits=(16, 2))
    datacil_credits_currency = fields.Char(compute='_compute_datacil_credits')
    datacil_credits_synced_at = fields.Datetime(compute='_compute_datacil_credits')

    @api.depends('company_id')
    def _compute_datacil_config_id(self):
        for settings in self:
            settings.datacil_config_id = self.env['datacil.config']._get_for_company(settings.company_id)

    @api.depends('datacil_config_id', 'datacil_api_key', 'datacil_api_url')
    def _compute_datacil_credits(self):
        for settings in self:
            config = settings.datacil_config_id
            settings.datacil_is_configured = bool(config and config._is_configured())
            settings.datacil_credits_balance = config.credits_balance if config else 0.0
            settings.datacil_credits_currency = (config and config.credits_currency) or _('credits')
            settings.datacil_credits_synced_at = config.credits_synced_at if config else False

    @api.model
    def get_values(self):
        res = super().get_values()
        config = self.env['datacil.config']._get_for_company()
        res.update({
            'datacil_api_url': config.api_url,
            'datacil_api_key': config.api_key,
            'datacil_api_version': config.api_version,
            'datacil_api_country': config.api_country,
            'datacil_api_delay': config.api_delay,
            'datacil_load_created_partners': config.load_created_partners,
        })
        return res

    def set_values(self):
        super().set_values()
        config = self.env['datacil.config']._get_or_create_for_company()
        values = {
            'api_url': self.datacil_api_url,
            'api_key': self.datacil_api_key,
            'api_version': self.datacil_api_version,
            'api_country': self.datacil_api_country,
            'api_delay': self.datacil_api_delay,
            'load_created_partners': self.datacil_load_created_partners,
        }
        # Only write what changed: avoids useless updates when opening settings.
        changed = {key: value for key, value in values.items() if config[key] != value}
        if changed:
            config.write(changed)
            if 'api_url' in changed:
                self.env['datacil.api'].clear_costs_cache()

    def action_datacil_refresh_credits(self):
        """Settings button: refresh the cached balance (also validates the key)."""
        result = self.env['datacil.api'].test_connection()
        return self._datacil_notify(result)

    def action_datacil_open_dashboard(self):
        return self.env['ir.actions.actions']._for_xml_id('datacil_client_odoo.action_datacil_dashboard')

    def _datacil_notify(self, result):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Datacil') if result['success'] else _('Datacil: connection failed'),
                'message': result['message'],
                'type': 'success' if result['success'] else 'danger',
                'sticky': not result['success'],
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }
