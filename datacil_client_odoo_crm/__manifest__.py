{
    'name': 'Datacil Client - CRM',
    'version': '18.0.2.1.0',
    'summary': 'Fill leads and opportunities from a cédula / RUC with Datacil',
    'description': """
Datacil for CRM
===============
Adds a **Cédula / RUC** field on leads and opportunities with a Datacil lookup
button (same loading screen and dialogs as the contact form).

* Fills the company or contact name, address, province, email and phone.
* Links the existing customer when the identification is already registered,
  instead of creating a duplicate later.
* Carries the identification over to the customer created from the lead.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Sales/CRM',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'crm'],
    'data': ['views/crm_lead_views.xml'],
    'auto_install': True,
    'installable': True,
}
