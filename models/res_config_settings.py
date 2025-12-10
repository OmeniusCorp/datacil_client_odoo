from odoo import fields, models, api
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    valid_ident_api_url = fields.Char(string="API URL")
    valid_ident_api_key = fields.Char(string="API Key")
    valid_ident_api_delay = fields.Float(string="Tiempo maximo de respuesta")
    valid_ident_load_created_partners = fields.Boolean(string="Permitir cargar clientes ya registrados")

    @api.model
    def get_values(self):
        res = super().get_values()
        config = self.env['ome.valid.identification'].search(
            [('company', '=', self.env.company.id)],
            limit=1
        )
        res.update({
            'valid_ident_api_url': config.api_url,
            'valid_ident_api_key': config.api_key,
            'valid_ident_api_delay': config.api_delay,
            'valid_ident_load_created_partners': config.load_created_partners,
        })
        return res

    def set_values(self):
        super().set_values()
        if not self.valid_ident_api_url or not self.valid_ident_api_key:
            raise UserError("Debe ingresar URL y API Key para guardar la configuración")
        company = self.env.company
        config = self.env['ome.valid.identification'].search(
            [('company', '=', company.id)],
            limit=1
        )
        if not config:
            config = self.env['ome.valid.identification'].create({
                'company': company.id,
            })
        config.write({
            'api_url': self.valid_ident_api_url,
            'api_key': self.valid_ident_api_key,
            'api_delay': self.valid_ident_api_delay,
            'load_created_partners': self.valid_ident_load_created_partners,
        })