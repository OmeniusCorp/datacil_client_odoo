from markupsafe import Markup

from odoo import api, fields, models, _

SECTION_ORDER = ['identity', 'licence', 'judicial', 'ant']


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    datacil_sections = fields.Json(string="Datacil Sections", copy=False, groups="hr.group_hr_user")
    datacil_info = fields.Html(string="Datacil Information", compute='_compute_datacil_info', sanitize=False,
                               groups="hr.group_hr_user")
    datacil_last_sync = fields.Datetime(string="Datacil Last Query", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_has_licence = fields.Boolean(string="Has Driver Licence", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_licence_type = fields.Char(string="Licence Type", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_licence_valid_from = fields.Date(string="Licence Valid From", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_licence_valid_until = fields.Date(string="Licence Valid Until", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_licence_expired = fields.Boolean(string="Licence Expired", compute='_compute_datacil_licence_expired', groups="hr.group_hr_user")
    datacil_licence_points = fields.Float(string="Licence Points", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_licence_points_max = fields.Float(string="Licence Points Max", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_judicial_count = fields.Integer(string="Judicial Cases", readonly=True, copy=False, groups="hr.group_hr_user")
    datacil_ant_citations = fields.Integer(string="ANT Citations", readonly=True, copy=False, groups="hr.group_hr_user")

    @api.depends('datacil_licence_valid_until')
    def _compute_datacil_licence_expired(self):
        today = fields.Date.context_today(self)
        for employee in self:
            employee.datacil_licence_expired = bool(
                employee.datacil_licence_valid_until and employee.datacil_licence_valid_until < today)

    @api.depends('datacil_sections')
    def _compute_datacil_info(self):
        for employee in self:
            sections = employee.datacil_sections or {}
            html = Markup('')
            for key in SECTION_ORDER + [k for k in sections if k not in SECTION_ORDER]:
                section = sections.get(key)
                if not section:
                    continue
                html += Markup(
                    '<div class="o_datacil_section mb-3">'
                    '<h5 class="mb-1">%s <small class="text-muted fw-normal">(%s)</small></h5>%s</div>'
                ) % (section.get('title', key), section.get('date', ''), Markup(section.get('html', '')))
            employee.datacil_info = html or False

    # ------------------------------------------------------------------
    # Widget entry points (record methods, require a saved employee)
    # ------------------------------------------------------------------
    def datacil_check_identity(self, identification=None):
        self.ensure_one()
        api_model = self.env['datacil.api']
        result = api_model.lookup_identification(identification or self.identification_id)
        if not result['success']:
            return result
        values = self._datacil_identity_values(result)
        data = result['data'] or {}
        rows = [
            (_('Name'), data.get('name')),
            (_('Birth Date'), data.get('birthDate')),
            (_('Age'), (data.get('elapsed') or {}).get('text')),
            (_('Gender'), data.get('gender')),
            (_('Address'), (data.get('address') or {}).get('completeAddress')),
            (_('Email'), (data.get('contact') or {}).get('email')),
            (_('Mobile'), (data.get('contact') or {}).get('cellphone')),
        ]
        html = api_model.format_html({label: value for label, value in rows if value})
        self._datacil_store_section('identity', _('Identity (cédula)'), html, values)
        return self._datacil_response(result, _('Identity verified'), rows)

    def datacil_check_licence(self, identification=None):
        self.ensure_one()
        api_model = self.env['datacil.api']
        result = api_model.get_licence(identification or self.identification_id)
        if not result['success']:
            if result['code'] == 'not_found':
                self._datacil_store_section('licence', _('Driver licence'), api_model.format_html(_('No licence found.')),
                                            {'datacil_has_licence': False, 'datacil_licence_type': False,
                                             'datacil_licence_valid_from': False, 'datacil_licence_valid_until': False,
                                             'datacil_licence_points': 0, 'datacil_licence_points_max': 0})
                result.update(success=True, code='ok', values={}, reload=True, title=_('Driver licence'),
                              rows=[{'label': _('Licence'), 'value': _('No licence found for this identification.')}])
            return result
        data = result['data'] or {}
        licences = [lic for lic in (data.get('licences') or []) if isinstance(lic, dict)]
        values, current, points = self._datacil_licence_values(data)
        rows = [
            (_('Has licence'), _('Yes') if values['datacil_has_licence'] else _('No')),
            (_('Type'), values['datacil_licence_type']),
            (_('Valid from'), values['datacil_licence_valid_from']),
            (_('Valid until'), values['datacil_licence_valid_until']),
            (_('Points'), f"{points.get('current')}/{points.get('max')}" if points else None),
            (_('Licences on file'), str(len(licences)) if len(licences) > 1 else None),
        ]
        html = api_model.format_html({'licences': licences, 'points': points})
        self._datacil_store_section('licence', _('Driver licence'), html, values)
        return self._datacil_response(result, _('Driver licence'), rows, html)

    def datacil_check_judicial(self, identification=None):
        self.ensure_one()
        api_model = self.env['datacil.api']
        result = api_model.get_judicial_cases(identification or self.identification_id)
        if not result['success']:
            return result
        data = result['data']
        cases = self._datacil_as_list(data, 'causas', 'cases', 'items', 'results')
        count = self.env['datacil.api'].as_count(data, 'causas', 'cases', 'items', 'results') or len(cases)
        values = {'datacil_judicial_count': count}
        rows = [(_('Judicial cases found'), str(count))]
        html = api_model.format_html(cases if cases else _('No judicial cases found.'))
        self._datacil_store_section('judicial', _('Judicial records'), html, values)
        return self._datacil_response(result, _('Judicial records'), rows, html)

    def datacil_check_ant(self, identification=None):
        """ANT citations and account statement (two paid queries)."""
        self.ensure_one()
        api_model = self.env['datacil.api']
        identification = identification or self.identification_id
        citations = api_model.get_ant_citations(identification)
        if not citations['success'] and citations['code'] != 'not_found':
            return citations
        debt = api_model.get_ant_debt(identification)
        if not debt['success'] and debt['code'] != 'not_found':
            return debt
        citation_list = self._datacil_as_list(citations['data'], 'citaciones', 'citations', 'items') if citations['success'] else []
        citation_count = api_model.as_count(citations['data'], 'citaciones', 'citations', 'items') if citations['success'] else 0
        values = {'datacil_ant_citations': citation_count or len(citation_list)}
        rows = [
            (_('ANT citations'), str(values['datacil_ant_citations'])),
            (_('ANT debt'), f"{api_model.as_amount(debt['data']):.2f}" if debt['success'] else _('No record')),
        ]
        html = api_model.format_html({
            _('Citations'): citation_list or _('No citations.'),
            _('Account statement'): debt['data'] if debt['success'] else _('No record in the ANT.'),
        })
        self._datacil_store_section('ant', _('ANT (citations and debt)'), html, values)
        return self._datacil_response(citations if citations['success'] else debt, _('ANT (citations and debt)'), rows, html)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _datacil_as_list(self, data, *keys):
        return self.env['datacil.api'].as_list(data, *keys)

    def _datacil_identity_values(self, result):
        """Fill the native personal fields, without overwriting what HR entered."""
        api_model = self.env['datacil.api']
        data = result['data'] or {}
        contact = data.get('contact') or {}
        country = self.env.ref('base.ec', raise_if_not_found=False)
        address = api_model.parse_address(data.get('address'))
        state = self.env['res.partner']._datacil_find_state(address['state'], country)
        candidates = {
            # Identity
            'identification_id': result.get('identification'),
            'birthday': data.get('birthDate'),
            'sex': data.get('gender') if data.get('gender') in ('male', 'female') else False,
            'country_id': country.id if country else False,            # Nationality
            # Private address
            'private_street': address['street'],
            'private_street2': address['street2'],
            'private_city': address['city'],
            'private_zip': address['zip'],
            'private_state_id': state.id if state else False,
            'private_country_id': country.id if country else False,
            # Private contact
            'private_email': api_model.as_text(contact.get('email')).lower(),
            'private_phone': api_model.as_text(contact.get('cellphone') or contact.get('phone')),
        }
        values = {name: value for name, value in candidates.items()
                  if value and name in self._fields and not self[name]}
        official_name = api_model.as_text(data.get('name'))
        if official_name and self._datacil_legal_name_is_default():
            # legal_name defaults to the employee name: the registry name is better.
            values['legal_name'] = official_name
        return values

    def _datacil_legal_name_is_default(self):
        """True while nobody set a legal name different from the employee name."""
        return 'legal_name' in self._fields and self.legal_name in (False, '', self.name)

    def _datacil_licence_values(self, data):
        """Licence summary, and the native work-permit-style fields when empty."""
        licences = [lic for lic in (data.get('licences') or []) if isinstance(lic, dict)]
        active = [lic for lic in licences if lic.get('isActive')] or licences
        current = active[0] if active else {}
        points = data.get('points') or {}
        values = {
            'datacil_has_licence': bool(data.get('hasLicence')),
            'datacil_licence_type': current.get('type') or False,
            'datacil_licence_valid_until': current.get('validUntil') or False,
            'datacil_licence_valid_from': current.get('validFrom') or False,
            'datacil_licence_points': float(points.get('current') or 0),
            'datacil_licence_points_max': float(points.get('max') or 0),
        }
        holder = self.env['datacil.api'].as_text(data.get('holder'))
        if holder and self._datacil_legal_name_is_default():
            values['legal_name'] = holder
        return values, current, points

    def _datacil_store_section(self, key, title, html, values):
        sections = dict(self.datacil_sections or {})
        sections[key] = {'title': title, 'html': str(html), 'date': fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}
        self.write(dict(values, datacil_sections=sections, datacil_last_sync=fields.Datetime.now()))
        self.message_post(
            body=Markup('<p><b>%s</b></p>%s') % (_('Datacil: %s', title), html),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _datacil_response(self, result, title, rows, html=None):
        response = dict(result)
        response.update({
            'title': title,
            'values': {},
            'reload': True,
            'rows': [{'label': label, 'value': value} for label, value in rows if value not in (None, '', False)],
            'html': str(html) if html else '',
            'credits': self.env['res.partner']._datacil_credits_info(self.env['datacil.api']._get_config()),
        })
        response.pop('data', None)
        response.pop('meta', None)
        return response
