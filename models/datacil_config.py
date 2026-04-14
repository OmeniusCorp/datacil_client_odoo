from odoo import fields, models

class DatacilConfig(models.Model):
    _name = "datacil.config"
    _description = "Configuracion de Validacion de Identificacion"
    _rec_name = "company"

    company = fields.Many2one(
        "res.company",
        string="Compañia", 
        required=True,
        ondelete="cascade", 
        default=lambda self: self.env.company,
    )
    api_url = fields.Char(string="URL", default='https://api.datacil.com', required=False)
    api_key = fields.Char(string="API Key", required=False)
    api_delay = fields.Float(string="Tiempo de respuesta", default=10)
    api_version = fields.Selection(
        selection=[('v1', 'Version 1')],
        string='API Version',
        default='v1'
    )
    api_country = fields.Selection(
        selection=[('ecuador', 'Ecuador')],
        string='API Country',
        default='ecuador'
    )
    load_created_partners = fields.Boolean(string="Permitir cargar clientes ya registrados", default=True)