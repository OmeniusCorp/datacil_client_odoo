{
    'name': 'Omenius Valid Identification',
    'version': '19.0.1.0.0',
    'summary': 'Validar cédula o RUC y autocompletar datos del cliente',
    'description': """
        Módulo para validar cédula o RUC desde el formulario del cliente y autocompletar los datos automáticamente.
    """,
    'author': 'Omenius',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'l10n_latam_base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/contact/res_partner_view.xml',
        'views/config/res_config_settings_views.xml',
        'views/contact/contact_views.xml',
        'views/actions/submenu_datacil.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'omenius_valid_identification/static/src/pages/**/*',
        ]
    },
    'installable': True,
    'application': False,
}
