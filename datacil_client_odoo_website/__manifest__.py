{
    'name': 'Datacil Client - Website',
    'version': '18.0.2.1.0',
    'summary': 'Autocomplete website address forms from a cédula / RUC with Datacil',
    'description': """
Datacil for Website
===================
Per-website option (Website › Settings › Datacil) to autocomplete the address
form of the checkout and the customer portal when the visitor enters a cédula
or RUC:

* **Name only**: uses the free Datacil name endpoint (no credits).
* **Full data**: name, address, province, phone and email (uses credits).

Only empty fields are filled, other customers are never exposed and lookups are
limited per visitor session.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Website/Website',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'website'],
    'data': ['views/res_config_settings_views.xml', 'views/address_templates.xml'],
    'assets': {
        'web.assets_frontend': ['datacil_client_odoo_website/static/src/js/**/*'],
    },
    'auto_install': True,
    'installable': True,
}
