from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    datacil_website_autocomplete = fields.Boolean(related='website_id.datacil_autocomplete', readonly=False)
    datacil_website_autocomplete_mode = fields.Selection(related='website_id.datacil_autocomplete_mode', readonly=False)
