from odoo import api, fields, models, _

RUC_STATUS = [
    ('active', 'Active'),
    ('suspended', 'Suspended'),
    ('canceled', 'Canceled'),
]
RUC_REGIME = [
    ('rimpe', 'RIMPE'),
    ('general', 'General'),
    ('unknown', 'Unknown'),
]
PROFILE_TYPE = [
    ('individual', 'Individual'),
    ('company', 'Company'),
    ('public_entity', 'Public Entity'),
    ('unknown', 'Unknown'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    datacil_last_sync = fields.Datetime(string="Datacil Last Query", readonly=True, copy=False)
    datacil_kind = fields.Selection(
        [('cedula', 'Cédula'), ('ruc', 'RUC')], string="Datacil Identification Type", readonly=True, copy=False)
    datacil_ruc_status = fields.Selection(RUC_STATUS, string="RUC Status (SRI)", readonly=True, copy=False)
    datacil_regime = fields.Selection(RUC_REGIME, string="Tax Regime", readonly=True, copy=False)
    datacil_profile_type = fields.Selection(PROFILE_TYPE, string="Taxpayer Type", readonly=True, copy=False)
    datacil_activity = fields.Char(string="Economic Activity", readonly=True, copy=False)
    datacil_accounting_required = fields.Boolean(string="Accounting Required", readonly=True, copy=False)
    datacil_withholding_agent = fields.Boolean(string="Withholding Agent", readonly=True, copy=False)
    datacil_special_contributor = fields.Boolean(string="Special Contributor", readonly=True, copy=False)
    datacil_is_ghost = fields.Boolean(string="Ghost Company (SRI)", readonly=True, copy=False)
    datacil_warning = fields.Char(compute='_compute_datacil_warning', string="Datacil Warning")

    @api.depends('datacil_ruc_status', 'datacil_is_ghost', 'datacil_last_sync')
    def _compute_datacil_warning(self):
        for partner in self:
            warnings = []
            if partner.datacil_is_ghost:
                warnings.append(_("flagged as ghost company by the SRI"))
            if partner.datacil_ruc_status == 'suspended':
                warnings.append(_("RUC suspended"))
            elif partner.datacil_ruc_status == 'canceled':
                warnings.append(_("RUC canceled"))
            partner.datacil_warning = (
                _("Datacil: %(partner)s is %(issues)s.", partner=partner.display_name, issues=_(" and ").join(warnings))
                if warnings else ''
            )

    # ------------------------------------------------------------------
    # Lookup used by the form widget (works on new or existing records)
    # ------------------------------------------------------------------
    def datacil_lookup(self, identification):
        """Query Datacil and return values ready for the form widget.

        Never raises: the ``code`` tells the widget which screen to show.
        Returned ``values`` use the web format for many2one fields
        (``{'id': .., 'display_name': ..}``) so they can be fed to ``record.update``.
        """
        result = self._datacil_query(identification)
        if result.get('success'):
            result['values'] = self._datacil_to_web_values(result['values'])
        return result

    def _datacil_query(self, identification):
        """Query Datacil for ``identification`` and build the full response.

        ``values`` are in ORM format (many2one as ids); see :meth:`datacil_lookup`
        for the widget flavour.
        """
        api_model = self.env['datacil.api']
        identification = api_model.normalize_identification(identification)
        if not identification:
            return api_model._result(False, 'invalid', _('You must enter an identification number before validating.'))

        config = api_model._get_config()
        if not config or not config._is_configured():
            return api_model._result(False, 'not_configured', api_model._user_message('not_configured', ''))

        existing = self._datacil_find_existing(identification)
        if existing and not config.load_created_partners and existing not in self:
            result = api_model._result(
                False, 'already_exists',
                _('The identification number %(vat)s is already registered for: %(name)s', vat=identification, name=existing.display_name))
            result['existing_partner'] = {'id': existing.id, 'display_name': existing.display_name}
            return result

        result = api_model.lookup_identification(identification)
        if not result['success']:
            return result

        values = self._datacil_prepare_values(result)
        rows = self._datacil_summary_rows(result, values)
        response = api_model._result(True, 'ok', _('Identification successfully validated for %s', values.get('name', identification)))
        other = existing if existing and existing not in self else self.env['res.partner']
        response.update({
            'title': _('Datacil: information found'),
            'values': values,
            'rows': rows,
            'warning': _('The identification number %(vat)s is already registered for: %(name)s', vat=identification, name=other.display_name) if other else '',
            'existing_partner': {'id': other.id, 'display_name': other.display_name} if other else False,
            'credits': self._datacil_credits_info(config),
        })
        return response

    def datacil_enrich(self, identification=None):
        """Server-side variant: query Datacil and write the values on ``self``.

        Returns the full result (``values`` in ORM format) or raises on failure.
        """
        self.ensure_one()
        result = self.env['datacil.api']._raise_if_error(self._datacil_query(identification or self.vat))
        self.write(result['values'])
        return result

    def datacil_check_partner(self, identification=None):
        """Widget entry point for documents: refresh the partner data and flags.

        Meant to be inherited through :class:`datacil.partner.mixin`; on a
        partner it refreshes ``self``.
        """
        partner = self[:1]
        if not partner and identification:
            partner = self._datacil_find_existing(identification)
        if not partner:
            return self.env['datacil.api']._result(False, 'invalid', _('Select a contact with an identification number first.'))
        result = partner._datacil_query(identification or partner.vat)
        if result.get('success'):
            partner.write(result['values'])
            result['values'] = {}
            result['reload'] = True
            result['title'] = _('Datacil: %s updated', partner.display_name)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _datacil_find_existing(self, identification):
        return self.with_context(active_test=False).search([('vat', '=', identification)], limit=1)

    @api.model
    def _datacil_find_state(self, name, country):
        if not name or not country:
            return self.env['res.country.state']
        State = self.env['res.country.state']
        domain = [('country_id', '=', country.id)]
        return State.search(domain + [('name', '=ilike', name)], limit=1) or State.search(domain + [('name', 'ilike', name)], limit=1)

    @api.model
    def _datacil_credits_info(self, config):
        if not config or not config.credits_synced_at:
            return False
        return {'balance': config.credits_balance, 'currency': config.credits_currency or _('credits')}

    @api.model
    def _datacil_prepare_values(self, result):
        """Map a ``lookup_identification`` result to ``res.partner`` values (ORM format)."""
        api_model = self.env['datacil.api']
        data = result.get('data') or {}
        kind = result.get('kind')
        contact = data.get('contact') or {}
        profile = data.get('profile') or {}
        status = data.get('status') or {}
        activity = data.get('activity') or {}

        country = self.env.ref('base.ec', raise_if_not_found=False)
        address = api_model.parse_address(data.get('address'))
        state = self._datacil_find_state(address['state'], country)
        is_company = kind == 'ruc' and profile.get('type') in ('company', 'public_entity')

        values = {
            'name': api_model.as_text(data.get('name')),
            'vat': result.get('identification'),
            'street': address['street'],
            'street2': address['street2'],
            'city': address['city'],
            'zip': address['zip'],
            'email': api_model.as_text(contact.get('email')).lower(),
            'phone': api_model.as_text(contact.get('cellphone') or contact.get('phone')),
            'state_id': state.id if state else False,
            'country_id': country.id if country else False,
        }
        if is_company:
            values['company_type'] = 'company'
        if activity.get('main'):
            industry = self._datacil_find_industry(activity['main'])
            if industry:
                values['industry_id'] = industry.id
        values = {key: value for key, value in values.items() if value}

        # Localization (l10n_ec) identification type, when installed.
        if 'l10n_latam_identification_type_id' in self._fields:
            id_type = self.env.ref('l10n_ec.ec_ruc' if kind == 'ruc' else 'l10n_ec.ec_dni', raise_if_not_found=False)
            if id_type:
                values['l10n_latam_identification_type_id'] = id_type.id

        values.update({
            'datacil_last_sync': fields.Datetime.now(),
            'datacil_kind': kind,
            'datacil_ruc_status': status.get('code') if status.get('code') in dict(RUC_STATUS) else False,
            'datacil_regime': profile.get('regime') if profile.get('regime') in dict(RUC_REGIME) else False,
            'datacil_profile_type': profile.get('type') if profile.get('type') in dict(PROFILE_TYPE) else False,
            'datacil_activity': activity.get('main') or False,
            'datacil_accounting_required': bool(profile.get('accountingRequired')),
            'datacil_withholding_agent': bool(profile.get('withholdingAgent')),
            'datacil_special_contributor': bool(profile.get('specialContributor')),
            'datacil_is_ghost': bool(status.get('isGhost')),
        })
        return values

    @api.model
    def _datacil_find_industry(self, activity):
        """Link the SRI economic activity to an existing industry (never creates one)."""
        Industry = self.env['res.partner.industry']
        activity = (activity or '').strip()
        if not activity:
            return Industry
        industry = Industry.search([('name', '=ilike', activity)], limit=1)
        if industry:
            return industry
        # SRI activities are long sentences: try the leading words.
        head = activity.split('.')[0].split(',')[0].strip()
        if head and head != activity:
            industry = Industry.search([('name', '=ilike', head)], limit=1)
        return industry

    @api.model
    def _datacil_to_web_values(self, values):
        return self.env['datacil.api'].to_web_values(self._name, values)

    @api.model
    def _datacil_summary_rows(self, result, values):
        """Rows displayed in the result dialog: ``[{'label': .., 'value': ..}]``."""
        data = result.get('data') or {}
        contact = data.get('contact') or {}
        rows = [
            (_('Name'), values.get('name')),
            (_('Identification'), result.get('identification')),
            (_('Type'), dict(self._fields['datacil_profile_type']._description_selection(self.env)).get(values.get('datacil_profile_type'))
             if values.get('datacil_profile_type') else (_('RUC') if result.get('kind') == 'ruc' else _('Cédula'))),
            (_('RUC Status (SRI)'), dict(self._fields['datacil_ruc_status']._description_selection(self.env)).get(values.get('datacil_ruc_status'))),
            (_('Tax Regime'), dict(self._fields['datacil_regime']._description_selection(self.env)).get(values.get('datacil_regime'))),
            (_('Economic Activity'), values.get('datacil_activity')),
            (_('Street'), values.get('street')),
            (_('Street 2'), values.get('street2')),
            (_('City'), values.get('city')),
            (_('ZIP'), values.get('zip')),
            (_('State'), self.env['res.country.state'].browse(values['state_id']).display_name if values.get('state_id') else None),
            (_('Email'), contact.get('email')),
            (_('Mobile'), contact.get('cellphone')),
            (_('Phone'), contact.get('phone')),
            (_('Industry'), self.env['res.partner.industry'].browse(values['industry_id']).display_name if values.get('industry_id') else None),
            (_('Birth Date'), data.get('birthDate')),
            (_('Age'), (data.get('elapsed') or {}).get('text')),
        ]
        representatives = [rep.get('name') for rep in (data.get('legalRepresentatives') or []) if isinstance(rep, dict) and rep.get('name')]
        if representatives:
            rows.append((_('Legal representative'), ', '.join(representatives)))
        if values.get('datacil_is_ghost'):
            rows.append((_('Warning'), _('Flagged as ghost company by the SRI')))
        return [{'label': label, 'value': value} for label, value in rows if value]
