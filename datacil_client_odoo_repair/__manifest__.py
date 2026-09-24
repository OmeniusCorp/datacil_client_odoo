{
    'name': 'Datacil Client - Repairs',
    'version': '18.0.2.1.0',
    'summary': 'SRI status warnings and Datacil checks on repair orders (workshop)',
    'description': """
Datacil for Repairs (workshop)
==============================
* Warning banner on repair orders when the customer's RUC is suspended,
  canceled or flagged as ghost company by the SRI.
* *Check in Datacil* button to refresh the customer data and flags from the
  repair order.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Inventory/Inventory',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'repair'],
    'data': ['views/repair_order_views.xml'],
    'auto_install': True,
    'installable': True,
}
