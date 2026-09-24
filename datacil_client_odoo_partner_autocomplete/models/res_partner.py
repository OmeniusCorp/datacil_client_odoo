from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # Native autocomplete entry points (called by partner_autocomplete JS)
    # ------------------------------------------------------------------
    @api.model
    def autocomplete_by_name(self, query, query_country_id, timeout=15):
        api_model = self.env['datacil.api']
        if api_model.is_configured():
            identification = api_model.normalize_identification(query)
            if api_model.identification_kind(query) and identification == query.strip():
                return self._datacil_suggestions_by_identification(identification)
            if self._datacil_autocomplete_active(query_country_id):
                result = api_model.autocomplete_companies(query)
                if result['success']:
                    return self._datacil_company_suggestions(result['data'])
        return super().autocomplete_by_name(query, query_country_id, timeout=timeout)

    @api.model
    def autocomplete_by_vat(self, vat, query_country_id, timeout=15):
        api_model = self.env['datacil.api']
        if api_model.is_configured() and api_model.identification_kind(vat):
            return self._datacil_suggestions_by_identification(api_model.normalize_identification(vat))
        return super().autocomplete_by_vat(vat, query_country_id, timeout=timeout)

    @api.model
    def enrich_by_duns(self, duns, timeout=15):
        suggestion = self.env.context.get('enriched_company_data') or {}
        if suggestion.get('datacil_id'):
            return self._datacil_enrich_suggestion(suggestion['datacil_id'])
        return super().enrich_by_duns(duns, timeout=timeout)

    def enrich_company_message_post(self, data):
        """Log a Datacil card instead of the DnB one when the data came from Datacil."""
        self.ensure_one()
        recently = fields.Datetime.now() - timedelta(minutes=5)
        from_datacil = self.datacil_kind and (not self.datacil_last_sync or self.datacil_last_sync >= recently)
        if from_datacil:
            if not self.datacil_last_sync:
                # Written here because the widget cannot carry a datetime.
                self.datacil_last_sync = fields.Datetime.now()
            rows = {
                _('Identification'): self.vat,
                _('Type'): dict(self._fields['datacil_profile_type']._description_selection(self.env)).get(self.datacil_profile_type),
                _('RUC Status (SRI)'): dict(self._fields['datacil_ruc_status']._description_selection(self.env)).get(self.datacil_ruc_status),
                _('Tax Regime'): dict(self._fields['datacil_regime']._description_selection(self.env)).get(self.datacil_regime),
                _('Economic Activity'): self.datacil_activity,
                _('Address'): ', '.join(filter(None, [self.street, self.city, self.state_id.name])),
                _('Phone'): self.phone,
                _('Email'): self.email,
            }
            html = self.env['datacil.api'].format_html({k: v for k, v in rows.items() if v})
            self.message_post(
                body=Markup('<p><b>%s</b></p>%s') % (_('Contact enriched with Datacil'), html),
                message_type='comment', subtype_xmlid='mail.mt_note')
            return
        return super().enrich_company_message_post(data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _datacil_autocomplete_active(self, query_country_id):
        """Datacil serves Ecuador only; worldwide searches (0) stay on IAP."""
        ecuador = self.env.ref('base.ec', raise_if_not_found=False)
        # The widget sends 0 for "search worldwide" and false for "no country":
        # in python both are falsy, so the type tells them apart.
        worldwide = query_country_id == 0 and not isinstance(query_country_id, bool)
        if not ecuador or worldwide:
            return False
        if query_country_id and query_country_id != ecuador.id:
            return False
        # No country typed: Datacil answers when it is configured for Ecuador,
        # even if the company country was never filled in.
        config = self.env['datacil.api']._get_config()
        return bool(query_country_id) or (config and config.api_country == 'ecuador') \
            or self.env.company.country_id == ecuador

    @api.model
    def _datacil_country_value(self):
        ecuador = self.env.ref('base.ec', raise_if_not_found=False)
        return {'id': ecuador.id, 'display_name': ecuador.display_name} if ecuador else False

    @api.model
    def _datacil_suggestions_by_identification(self, identification):
        api_model = self.env['datacil.api']
        result = api_model.get_name(identification)
        if not result['success']:
            return []
        data = result['data'] if isinstance(result['data'], dict) else {}
        name = api_model.pick(data, 'name', 'nombre', 'razonSocial', 'razon_social')
        if not name:
            return []
        return [{
            'name': name,
            'vat': identification,
            'duns': identification,
            'datacil_id': identification,
            'city': '',
            'country_id': self._datacil_country_value(),
        }]

    @api.model
    def _datacil_company_suggestions(self, data):
        api_model = self.env['datacil.api']
        items = data if isinstance(data, list) else api_model.pick(data, 'empresas', 'suggestions', 'items', 'results', 'companies', default=[])
        suggestions = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            ruc = api_model.normalize_identification(str(api_model.pick(item, 'ruc', 'id', default='')))
            name = api_model.pick(item, 'razonSocial', 'razon_social', 'name', 'nombre', 'nombreComercial')
            if not ruc or not name:
                continue
            suggestions.append({
                'name': name,
                'vat': ruc,
                'duns': ruc,
                'datacil_id': ruc,
                'city': api_model.pick(item, 'provincia', 'province', 'state', 'ciudad', default='') or '',
                'country_id': self._datacil_country_value(),
            })
        return suggestions

    @api.model
    def _datacil_enrich_suggestion(self, identification):
        """Paid lookup once a suggestion is selected; same contract as IAP enrichment."""
        api_model = self.env['datacil.api']
        result = api_model.lookup_identification(identification)
        if not result['success']:
            error = 'Insufficient Credit' if result['code'] == 'no_credits' else result['message']
            return {'error': True, 'error_message': error}
        web_values = self._datacil_to_web_values(self._datacil_prepare_values(result))
        # The native autocomplete pushes these values into `record.update()`,
        # which only accepts luxon objects for date/datetime fields. The query
        # date is written server side instead (see enrich_company_message_post).
        return {name: value for name, value in web_values.items()
                if self._fields[name].type not in ('date', 'datetime')}
