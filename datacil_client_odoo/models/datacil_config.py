from odoo import api, fields, models, _

# Cached credit balance is considered fresh for this many seconds.
CREDITS_CACHE_TTL = 300


class DatacilConfig(models.Model):
    _name = "datacil.config"
    _description = "Datacil Configuration"
    _rec_name = "company"

    company = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.company,
        index=True,
    )
    api_url = fields.Char(string="URL", default='https://api.datacil.com')
    api_key = fields.Char(string="API Key", groups="base.group_system")
    api_delay = fields.Float(string="Response Time", default=10, help="Seconds to wait for the API response.")
    api_version = fields.Selection(
        selection=[('v1', 'Version 1')],
        string='API Version',
        default='v1',
    )
    api_country = fields.Selection(
        selection=[('ecuador', 'Ecuador')],
        string='API Country',
        default='ecuador',
    )
    load_created_partners = fields.Boolean(string="Allow loading already registered customers", default=True)

    # Cached credit balance (refreshed on demand or after paid queries).
    credits_balance = fields.Float(string="Credits", readonly=True, digits=(16, 2))
    credits_currency = fields.Char(string="Credits Unit", readonly=True)
    credits_synced_at = fields.Datetime(string="Credits Last Sync", readonly=True)

    _sql_constraints = [
        ('company_uniq', 'unique(company)', 'There is already a Datacil configuration for this company.'),
    ]

    @api.model
    def _get_for_company(self, company=None):
        """Return the configuration of ``company`` (default: current company)."""
        company = company or self.env.company
        return self.sudo().search([('company', '=', company.id)], limit=1)

    @api.model
    def _get_or_create_for_company(self, company=None):
        company = company or self.env.company
        config = self._get_for_company(company)
        if not config:
            config = self.sudo().create({'company': company.id})
        return config

    def _is_configured(self):
        self.ensure_one()
        return bool(self.api_url and self.api_key and self.api_country and self.api_version)

    def _credits_are_fresh(self):
        self.ensure_one()
        if not self.credits_synced_at:
            return False
        age = (fields.Datetime.now() - self.credits_synced_at).total_seconds()
        return age < CREDITS_CACHE_TTL

    def _update_credits_cache(self, data):
        """Store the balance returned by ``/usage/credits`` (best effort)."""
        self.ensure_one()
        if not isinstance(data, dict):
            return
        balance = data.get('balance', data.get('credits'))
        if balance is None:
            return
        try:
            balance = float(balance)
        except (TypeError, ValueError):
            return
        self.sudo().write({
            'credits_balance': balance,
            'credits_currency': data.get('currency') or _('credits'),
            'credits_synced_at': fields.Datetime.now(),
        })
