{
    'name': 'Datacil Ventas Ecuador - Alerta de RUC suspendido o empresa fantasma',
    'version': '19.0.2.1.0',
    'summary': 'Avisa en presupuestos y pedidos cuando el RUC del cliente esta suspendido, cancelado o es empresa fantasma (SRI)',
    'description': """
Datacil for Sales
=================
* Warning banner on quotations and sales orders when the customer's RUC is
  suspended, canceled or flagged as ghost company by the SRI (data kept on the
  contact by the Datacil Client module).
* *Check in Datacil* button to refresh the customer data and flags without
  leaving the order.

What it shows
-------------
The warning reads the SRI data already stored on the contact, so opening an
order costs nothing. Verifying queries Datacil and refreshes the customer.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Sales/Sales',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'sale'],
    'data': ['views/sale_order_views.xml'],
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
