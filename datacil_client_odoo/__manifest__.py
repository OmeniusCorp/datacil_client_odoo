{
    'name': 'Datacil Client Ecuador - Consultar Cedula y RUC Autocompletar datos',
    'version': '17.0.1.0.0',
    'summary': 'Validate ID or Tax ID and autocomplete customer data',
    'description': """
        Module to validate ID or Tax ID from the customer form and autocomplete data automatically using Datacil services.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'category': 'Productivity',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'l10n_latam_base', 'web', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/actions/submenu_datacil.xml',
        'views/contact/res_partner_view.xml',
        'views/config/res_config_settings_views.xml',
        'views/contact/contact_views.xml',
        'data/datacil_config.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'datacil_client_odoo/static/src/pages/**/*',
        ]
    },
    'website': 'https://datacil.com',
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
}
