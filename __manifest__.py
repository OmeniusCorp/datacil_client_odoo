{
    'name': 'Omenius Valid Identification',
    'version': '19.0.1.0.0',
    'summary': 'Validar cédula o RUC y autocompletar datos del cliente',
    'description': """
        Módulo para validar cédula o RUC desde el formulario del cliente y autocompletar los datos automáticamente.
    """,
    'author': 'Omenius',
    'website': 'https://megamayorista.net',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'l10n_latam_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
