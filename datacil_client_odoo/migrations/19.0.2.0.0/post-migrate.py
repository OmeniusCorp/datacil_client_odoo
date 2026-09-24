import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Install the companion modules whose app is already installed.

    A module upgrade only pulls missing *dependencies*; it never installs
    ``auto_install`` modules that depend on the upgraded one. Do it here once
    so existing databases get the POS/CRM/Sales/... integrations on upgrade.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Module = env['ir.module.module']
    try:
        Module.update_list()
        companions = Module.search([
            ('name', '=like', 'datacil_client_odoo_%'),
            ('state', '=', 'uninstalled'),
            ('auto_install', '=', True),
        ])
        to_install = companions.filtered(lambda module: all(
            dep.state == 'installed' or dep.name == 'datacil_client_odoo'
            for dep in module.dependencies_id
        ))
        if to_install:
            _logger.info("Datacil: installing companion modules %s", to_install.mapped('name'))
            to_install.button_install()
    except Exception:  # noqa: BLE001 - never block the upgrade because of this
        _logger.exception("Datacil: could not auto-install companion modules")
