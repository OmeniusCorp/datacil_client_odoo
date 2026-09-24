{
    'name': 'Datacil Client - Employees',
    'version': '18.0.2.1.0',
    'summary': 'Identity, driver licence, judicial and ANT checks for employees with Datacil',
    'description': """
Datacil for Employees
=====================
Adds a **Datacil** tab on the employee form (HR officers only) with buttons that
query the employee's identification number:

* **Verify identity**: fills the empty personal fields (birthday, gender,
  private address, email and phone) without overwriting existing data.
* **Driver licence**: type, validity and points balance.
* **Judicial records**: cases where the person appears as plaintiff or defendant.
* **ANT citations & debt**: traffic citations and account statement.

Every result is kept in the tab and logged as a note in the employee chatter.
    """,
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Human Resources/Employees',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'hr'],
    'data': ['views/hr_employee_views.xml'],
    'auto_install': True,
    'installable': True,
}
