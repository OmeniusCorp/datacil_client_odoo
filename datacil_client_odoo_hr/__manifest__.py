{
    'name': 'Datacil Empleados Ecuador - Identidad, licencia y antecedentes por cedula',
    'version': '18.0.2.1.0',
    'summary': 'Completa la ficha personal desde la cedula y consulta licencia de conducir, antecedentes judiciales y ANT',
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

Native fields filled (only when empty)
--------------------------------------
Identification number, birthday, gender, nationality, private
address (street, street 2, city, zip, state, country), private email and phone.
Driver licence, judicial records and ANT data are kept in the Datacil tab,
since Odoo has no native field for them.
""",
    'author': 'Datacil',
    'support': 'soporte@datacil.com',
    'website': 'https://datacil.com',
    'category': 'Human Resources/Employees',
    'license': 'LGPL-3',
    'depends': ['datacil_client_odoo', 'hr'],
    'data': ['views/hr_employee_views.xml'],
    'images': ['static/description/banner.jpg'],
    'auto_install': True,
    'installable': True,
    'application': False,
}
