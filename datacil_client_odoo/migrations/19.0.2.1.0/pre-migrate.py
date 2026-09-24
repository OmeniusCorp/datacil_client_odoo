import logging

_logger = logging.getLogger(__name__)

OLD_MODULE = 'datacil_client_odoo_pos'


def migrate(cr, version):
    """The Point of Sale integration now lives in this module.

    Databases that installed the former ``datacil_client_odoo_pos`` companion
    (its only content was one access rule, now defined here) get it removed so
    Odoo does not keep an "installed" module without code on disk.
    """
    cr.execute("SELECT id, state FROM ir_module_module WHERE name = %s", (OLD_MODULE,))
    row = cr.fetchone()
    if not row:
        return
    module_id, state = row
    _logger.info("Datacil: removing the merged %s module (state %s)", OLD_MODULE, state)
    cr.execute("SAVEPOINT datacil_drop_pos")
    try:
        cr.execute("""
            DELETE FROM ir_model_access
             WHERE id IN (SELECT res_id FROM ir_model_data
                           WHERE module = %s AND model = 'ir.model.access')
        """, (OLD_MODULE,))
        cr.execute("DELETE FROM ir_model_data WHERE module = %s", (OLD_MODULE,))
        for table in ('ir_module_module_dependency', 'ir_module_module_exclusion', 'module_country'):
            cr.execute(f"DELETE FROM {table} WHERE module_id = %s", (module_id,))
        cr.execute("DELETE FROM ir_module_module_dependency WHERE name = %s", (OLD_MODULE,))
        cr.execute("DELETE FROM ir_module_module WHERE id = %s", (module_id,))
        cr.execute("RELEASE SAVEPOINT datacil_drop_pos")
    except Exception:  # noqa: BLE001 - never block the upgrade
        cr.execute("ROLLBACK TO SAVEPOINT datacil_drop_pos")
        _logger.warning("Datacil: could not delete %s, marking it uninstalled instead", OLD_MODULE, exc_info=True)
        cr.execute("UPDATE ir_module_module SET state = 'uninstalled' WHERE id = %s", (module_id,))
