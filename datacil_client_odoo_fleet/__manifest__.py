{
    'name': 'Datacil Ecuador - Validar Cedula y RUC, autocompletar contactos y POS',
    'version': '18.0.2.1.0',
    'summary': 'Valida cedula (10 digitos) y RUC (13 digitos) del SRI y autocompleta el contacto en Odoo y en el Punto de Venta',
    'description': """
Datacil Client for Odoo
=======================
Query Ecuadorian identification numbers (cédula, 10 digits, or RUC, 13 digits) on
the Datacil API and autocomplete the contact with the data returned by the SRI.

Contacts
--------
* **Validate** button next to the identification number on the contact form.
  Works on new (unsaved) and existing contacts, with an explicit loading screen
  and a result dialog to review the data before applying it.
* Dedicated feedback screens: Datacil not configured, no credits left, service
  unavailable, API key rejected, rate limit, invalid or unknown identification,
  contact already registered.
* *Datacil* tab on the contact with the SRI information (RUC status, tax
  regime, taxpayer type, economic activity, accounting / withholding flags,
  ghost company flag) and a warning used by the other apps.
* Identification type (cédula / RUC) set automatically when the Ecuadorian
  localization is installed.

Point of Sale
-------------
* The same button, loading screen and dialogs in the customer form opened from
  the Point of Sale.

Settings and dashboard
----------------------
* Settings › Datacil: API URL, key, timeout and duplicate handling, with a
  credits card (cached balance, refresh & connection test).
* Datacil dashboard (Contacts › Datacil): credit balance, transaction history
  and cost per service.

Companion modules
-----------------
Installed automatically when the related app is present: CRM, Sales, Purchase,
Repairs, Fleet, Employees, Website and the native Partner Autocomplete.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'category': 'Productivity',
    'license': 'LGPL-3',
    'depends': ['contacts', 'point_of_sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/datacil_config.xml',
        'views/datacil_dashboard_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'datacil_client_odoo/static/src/core/**/*',
            'datacil_client_odoo/static/src/dialogs/**/*',
            'datacil_client_odoo/static/src/widgets/**/*',
            'datacil_client_odoo/static/src/pages/**/*',
        ],
        # The POS renders the backend contact form with its own bundle.
        'point_of_sale._assets_pos': [
            'datacil_client_odoo/static/src/core/**/*',
            'datacil_client_odoo/static/src/dialogs/**/*',
            'datacil_client_odoo/static/src/widgets/**/*',
        ],
    },
    'website': 'https://datacil.com',
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
}
