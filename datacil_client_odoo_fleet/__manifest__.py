{
    'name': 'Datacil Client - Fleet',
    'version': '18.0.2.1.0',
    'summary': 'Enrich fleet vehicles from the license plate with Datacil',
    'description': """
Datacil for Fleet
=================
Adds a **Query plate in Datacil** button on the vehicle form (works on new
vehicles too):

* Fills the chassis number, color and model year; links the brand/model when
  it already exists in the fleet catalog.
* Links the registered owner as driver when the contact exists and no driver
  is assigned.
* Keeps the registered owner, pending fees and citation count returned by the
  ANT in a *Datacil* tab, and logs the full answer in the chatter.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Human Resources/Fleet',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'fleet'],
    'data': ['views/fleet_vehicle_views.xml'],
    'auto_install': True,
    'installable': True,
}
