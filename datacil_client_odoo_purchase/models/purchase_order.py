from odoo import fields, models


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'datacil.partner.mixin']

    datacil_partner_vat = fields.Char(related='partner_id.vat', string="Partner Identification")
    datacil_partner_warning = fields.Char(related='partner_id.datacil_warning')
    datacil_partner_last_sync = fields.Datetime(related='partner_id.datacil_last_sync')
