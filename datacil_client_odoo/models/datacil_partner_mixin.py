from odoo import models


class DatacilPartnerMixin(models.AbstractModel):
    """Shared behaviour for documents that have a ``partner_id`` (orders, repairs...).

    Inheriting models declare the related fields they display (kept on the
    concrete model so the mixin does not depend on ``partner_id`` existing here)::

        datacil_partner_vat = fields.Char(related='partner_id.vat')
        datacil_partner_warning = fields.Char(related='partner_id.datacil_warning')
    """
    _name = 'datacil.partner.mixin'
    _description = 'Datacil Partner Check'

    def datacil_check_partner(self, identification=None):
        """Refresh the document's partner from Datacil (widget entry point)."""
        partner = self[:1].partner_id if self else self.env['res.partner']
        return partner.datacil_check_partner(identification)
