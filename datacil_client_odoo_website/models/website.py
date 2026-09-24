from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    datacil_autocomplete = fields.Boolean(
        string="Datacil Autocomplete",
        help="Autocomplete the customer data on address forms from the cédula / RUC entered by the visitor.")
    datacil_autocomplete_mode = fields.Selection(
        [('name', 'Name only (free)'), ('full', 'Full data (uses credits)')],
        string="Datacil Autocomplete Mode", default='name', required=True)
