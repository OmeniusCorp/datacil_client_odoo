{
    'name': 'Datacil Autocompletar Contactos Ecuador - Cedula, RUC y razon social',
    'version': '18.0.2.1.0',
    'summary': 'Las sugerencias del autocompletado nativo de contactos se sirven desde Datacil para Ecuador, no desde Odoo IAP',
    'description': """
Datacil for Partner Autocomplete
================================
When Datacil is configured for the company, the native *Partner Autocomplete*
(suggestions while typing the name or Tax ID on the contact form) is served by
Datacil instead of Odoo IAP:

* Typing a cédula / RUC suggests the matching person or company (free endpoint).
* Typing a company name suggests Ecuadorian companies (free endpoint).
* Selecting a suggestion enriches the contact with the Datacil data (uses
  Datacil credits) and logs a Datacil card in the chatter.

Other countries and worldwide searches keep using Odoo IAP.

Native fields filled
--------------------
Name, identification, street, street 2, city, zip, state, country, email,
phone, plus the SRI information (RUC status, tax regime, taxpayer type and
economic activity). A Datacil card is logged in the chatter.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Productivity',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'partner_autocomplete'],
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
