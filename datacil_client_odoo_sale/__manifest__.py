{
    'name': 'Datacil Client - Sales',
    'version': '18.0.2.1.0',
    'summary': 'SRI status warnings and Datacil checks on quotations and sales orders',
    'description': """
Datacil for Sales
=================
* Warning banner on quotations and sales orders when the customer's RUC is
  suspended, canceled or flagged as ghost company by the SRI (data kept on the
  contact by the Datacil Client module).
* *Check in Datacil* button to refresh the customer data and flags without
  leaving the order.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Sales/Sales',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'sale'],
    'data': ['views/sale_order_views.xml'],
    'auto_install': True,
    'installable': True,
}
