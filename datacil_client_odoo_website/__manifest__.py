{
    'name': 'Datacil Sitio Web Ecuador - Autocompletar checkout con Cedula o RUC',
    'version': '18.0.2.1.0',
    'summary': 'El visitante escribe su cedula o RUC y el formulario de direccion del checkout y del portal se completa solo',
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

Native fields filled
--------------------
Name, company name, street, street 2, city, zip, state, country, phone and
email. Only the empty inputs of the form are filled, so the visitor keeps
control of their data.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Website/Website',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'website'],
    'data': ['views/res_config_settings_views.xml', 'views/address_templates.xml'],
    'assets': {
        'web.assets_frontend': ['datacil_client_odoo_website/static/src/interactions/**/*'],
    },
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
