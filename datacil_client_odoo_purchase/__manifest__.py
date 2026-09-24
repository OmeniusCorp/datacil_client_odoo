{
    'name': 'Datacil Client - Purchase',
    'version': '18.0.2.1.0',
    'summary': 'SRI status warnings and Datacil checks on requests for quotation and purchase orders',
    'description': """
Datacil for Purchase
====================
* Warning banner on requests for quotation and purchase orders when the vendor's
  RUC is suspended, canceled or flagged as ghost company by the SRI.
* *Check in Datacil* button to refresh the vendor data and flags without
  leaving the order.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Inventory/Purchase',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'purchase'],
    'data': ['views/purchase_order_views.xml'],
    'auto_install': True,
    'installable': True,
}
