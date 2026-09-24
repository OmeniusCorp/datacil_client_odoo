{
    'name': 'Datacil CRM Ecuador - Iniciativas y oportunidades desde Cedula o RUC',
    'version': '19.0.2.1.0',
    'summary': 'Llena iniciativas y oportunidades con los datos del SRI escribiendo la cedula o el RUC, sin duplicar clientes',
    'description': """
Datacil for CRM
===============
Adds a **Cédula / RUC** field on leads and opportunities with a Datacil lookup
button (same loading screen and dialogs as the contact form).

* Fills the company or contact name, address, province, email and phone.
* Links the existing customer when the identification is already registered,
  instead of creating a duplicate later.
* Carries the identification over to the customer created from the lead.

Native fields filled
--------------------
Company name or contact name, street, street 2, city, zip, state, country,
email, phone and industry. The customer is linked instead of duplicated when
the identification is already registered.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Sales/CRM',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'crm'],
    'data': ['views/crm_lead_views.xml'],
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
