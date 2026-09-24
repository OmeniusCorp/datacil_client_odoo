{
    'name': 'Datacil Client - Partner Autocomplete',
    'version': '18.0.2.1.0',
    'summary': 'Serve the native partner autocomplete from Datacil instead of Odoo IAP',
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
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Productivity',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'partner_autocomplete'],
    'auto_install': True,
    'installable': True,
}
