from odoo import fields, models, api, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    valid_ident_api_url = fields.Char(string="API URL")
    valid_ident_api_key = fields.Char(string="API Key")
    valid_ident_api_version = fields.Selection(
        selection=[
            ('v1', 'Version 1'),
        ],
        string='API Version',
        required=True
    )
    valid_ident_api_country = fields.Selection(
        selection=[
            ('ecuador', 'Ecuador'),
        ],
        string='API Country',
        required=True
    )
    valid_ident_api_delay = fields.Float(string="Maximum Response Time")
    valid_ident_load_created_partners = fields.Boolean(string="Allow loading already registered customers")

    @api.model
    def get_values(self):
        res = super().get_values()
        config = self.env['datacil.config'].search(
            [('company', '=', self.env.company.id)],
            limit=1
        )
        res.update({
            'valid_ident_api_url': config.api_url,
            'valid_ident_api_key': config.api_key,
            'valid_ident_api_version': config.api_version,
            'valid_ident_api_country': config.api_country,
            'valid_ident_api_delay': config.api_delay,
            'valid_ident_load_created_partners': config.load_created_partners,
        })
        return res

    def set_values(self):
        super().set_values()
        company = self.env.company
        config = self.env['datacil.config'].search(
            [('company', '=', company.id)],
            limit=1
        )
        if not config:
            config = self.env['datacil.config'].create({
                'company': company.id,
            })
        config.write({
            'api_url': self.valid_ident_api_url,
            'api_key': self.valid_ident_api_key,
            'api_version': self.valid_ident_api_version,
            'api_country': self.valid_ident_api_country,
            'api_delay': self.valid_ident_api_delay,
            'load_created_partners': self.valid_ident_load_created_partners,
        })
