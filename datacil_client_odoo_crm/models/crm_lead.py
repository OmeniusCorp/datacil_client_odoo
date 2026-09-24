from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    datacil_vat = fields.Char(string="Cédula / RUC", compute='_compute_datacil_vat', store=True, readonly=False)

    @api.depends('partner_id')
    def _compute_datacil_vat(self):
        # Keep in sync with the linked customer without overriding a manual entry.
        for lead in self:
            if lead.partner_id.vat and not lead.datacil_vat:
                lead.datacil_vat = lead.partner_id.vat

    def datacil_lookup(self, identification):
        """Query Datacil and translate partner values to lead fields."""
        result = self.env['res.partner'].datacil_lookup(identification)
        if not result.get('success'):
            return result
        partner_values = result.get('values') or {}
        values = {
            'datacil_vat': partner_values.get('vat'),
            'street': partner_values.get('street'),
            'street2': partner_values.get('street2'),
            'zip': partner_values.get('zip'),
            'city': partner_values.get('city'),
            'state_id': partner_values.get('state_id'),
            'country_id': partner_values.get('country_id'),
            'email_from': partner_values.get('email'),
            'phone': partner_values.get('phone'),
        }
        if partner_values.get('company_type') == 'company':
            values['partner_name'] = partner_values.get('name')
        else:
            values['contact_name'] = partner_values.get('name')
        if partner_values.get('industry_id'):
            values['industry_id'] = partner_values['industry_id']
        if result.get('existing_partner'):
            # Link the registered customer instead of duplicating it later.
            values['partner_id'] = result['existing_partner']
        result['values'] = {key: value for key, value in values.items() if value not in (None, '')}
        return result

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        values = super()._prepare_customer_values(partner_name, is_company=is_company, parent_id=parent_id)
        if self.datacil_vat and not parent_id:
            values.setdefault('vat', self.datacil_vat)
        return values
