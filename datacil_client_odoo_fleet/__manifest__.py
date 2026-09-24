{
    'name': 'Datacil Flota Ecuador - Datos del vehiculo por placa (ANT)',
    'version': '19.0.2.1.0',
    'summary': 'Consulta la placa y completa marca, modelo, chasis, avaluo, propietario, multas y citaciones desde la ANT',
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

Native fields filled
--------------------
License plate, brand and model (created in the fleet catalog when missing),
model year, chassis number (VIN), color, fuel type, transmission, seats, doors,
power, catalog value (appraisal), registration date and driver (when the
registered owner already exists as a contact).

The registered owner, vehicle class, service type, last registration, pending
fees and citation count are kept in a Datacil tab, along with the full answer.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Human Resources/Fleet',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'fleet'],
    'data': ['views/fleet_vehicle_views.xml'],
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
