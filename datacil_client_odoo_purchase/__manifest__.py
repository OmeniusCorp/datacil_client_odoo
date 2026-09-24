{
    'name': 'Datacil Compras Ecuador - Valida el RUC de tus proveedores',
    'version': '18.0.2.1.0',
    'summary': 'Avisa en pedidos de compra cuando el RUC del proveedor esta suspendido, cancelado o es empresa fantasma (SRI)',
    'description': """
Datacil for Purchase
====================
* Warning banner on requests for quotation and purchase orders when the vendor's
  RUC is suspended, canceled or flagged as ghost company by the SRI.
* *Check in Datacil* button to refresh the vendor data and flags without
  leaving the order.

What it shows
-------------
The warning reads the SRI data already stored on the contact, so opening an
order costs nothing. Verifying queries Datacil and refreshes the vendor.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Inventory/Purchase',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'purchase'],
    'data': ['views/purchase_order_views.xml'],
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
