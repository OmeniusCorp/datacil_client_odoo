{
    'name': 'Datacil Taller Ecuador - Clientes verificados en reparaciones',
    'version': '18.0.2.1.0',
    'summary': 'Valida cedula y RUC del cliente en las ordenes de reparacion y avisa del estado de su RUC en el SRI',
    'description': """
Datacil for Repairs (workshop)
==============================
* Warning banner on repair orders when the customer's RUC is suspended,
  canceled or flagged as ghost company by the SRI.
* *Check in Datacil* button to refresh the customer data and flags from the
  repair order.

What it shows
-------------
The warning reads the SRI data already stored on the contact, so opening a
repair order costs nothing. Verifying queries Datacil and refreshes the customer.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Inventory/Inventory',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'repair'],
    'data': ['views/repair_order_views.xml'],
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
