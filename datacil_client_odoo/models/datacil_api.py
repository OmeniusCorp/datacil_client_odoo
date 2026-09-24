import logging
import re
import time

import requests

from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Result codes returned by every ``datacil.api`` call. The JS side maps them
# to the proper feedback screen (see static/src/dialogs).
CODE_OK = 'ok'
CODE_NOT_CONFIGURED = 'not_configured'
CODE_NO_CREDITS = 'no_credits'
CODE_UNAVAILABLE = 'unavailable'
CODE_UNAUTHORIZED = 'unauthorized'
CODE_FORBIDDEN = 'forbidden'
CODE_RATE_LIMIT = 'rate_limit'
CODE_INVALID = 'invalid'
CODE_NOT_FOUND = 'not_found'
CODE_ERROR = 'error'

# Per-worker cache of the (public) endpoint costs: {(dbname, api_url): (timestamp, result)}
_COSTS_CACHE = {}
COSTS_CACHE_TTL = 3600

_CREDIT_WORDS = re.compile(r'cr[eé]dit|saldo|balance|insufficient|insuficiente', re.IGNORECASE)


class DatacilApi(models.AbstractModel):
    """Thin HTTP client for the Datacil API.

    Every public method returns a plain dict::

        {'success': bool, 'code': str, 'message': str, 'data': ..., 'meta': ..., 'status': int}

    Nothing is raised on API/network problems so callers can render a proper
    feedback screen; use :meth:`_raise_if_error` for server-side buttons.
    """
    _name = 'datacil.api'
    _description = 'Datacil API Client'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _result(self, success, code, message, data=None, meta=None, status=0):
        return {
            'success': success,
            'code': code,
            'message': message or '',
            'data': data if data is not None else {},
            'meta': meta or {},
            'status': status,
        }

    @api.model
    def _raise_if_error(self, result):
        if not result.get('success'):
            raise UserError(result.get('message') or _('Datacil query failed.'))
        return result

    @api.model
    def _get_config(self, company=None):
        return self.env['datacil.config']._get_for_company(company)

    @api.model
    def is_configured(self, company=None):
        config = self._get_config(company)
        return bool(config and config._is_configured())

    @api.model
    def normalize_identification(self, value):
        """Keep digits only (users often paste ``099-1234567``)."""
        return re.sub(r'\D', '', value or '')

    @api.model
    def identification_kind(self, value):
        """Return ``'cedula'`` (10 digits), ``'ruc'`` (13 digits) or ``False``."""
        value = self.normalize_identification(value)
        if len(value) == 10:
            return 'cedula'
        if len(value) == 13:
            return 'ruc'
        return False

    @api.model
    def _map_status(self, status, message):
        if status == 400:
            return CODE_INVALID
        if status == 401:
            return CODE_UNAUTHORIZED
        if status == 402:
            return CODE_NO_CREDITS
        if status == 403:
            return CODE_NO_CREDITS if _CREDIT_WORDS.search(message or '') else CODE_FORBIDDEN
        if status == 404:
            return CODE_NOT_FOUND
        if status == 429:
            return CODE_RATE_LIMIT
        if status >= 500:
            return CODE_UNAVAILABLE
        return CODE_ERROR

    @api.model
    def _user_message(self, code, api_message, status=0):
        """Translate an API failure into a message meant for end users."""
        messages = {
            CODE_NOT_CONFIGURED: _('Datacil is not configured for this company. Go to Settings › Datacil and enter your API key.'),
            CODE_NO_CREDITS: _('Your Datacil account has no credits left. Top up your balance to keep querying.'),
            CODE_UNAVAILABLE: _('The Datacil service is temporarily unavailable. Please try again in a few minutes.'),
            CODE_UNAUTHORIZED: _('The Datacil API key was rejected. Check it in Settings › Datacil.'),
            CODE_FORBIDDEN: _('Your Datacil account is not allowed to use this service.'),
            CODE_RATE_LIMIT: _('Too many queries in a short time. Please wait a moment and try again.'),
            CODE_INVALID: _('The identification entered is not valid for its type.'),
            CODE_NOT_FOUND: _('No information was found for the identification entered.'),
        }
        message = messages.get(code) or _('Unexpected error while querying Datacil.')
        if api_message and code in (CODE_INVALID, CODE_NOT_FOUND, CODE_FORBIDDEN, CODE_ERROR, CODE_UNAVAILABLE):
            message = f"{message} ({api_message})"
        return message

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    @api.model
    def _request(self, path, params=None, company=None, public=False, paid=False):
        """GET ``/{version}/{path}`` on the configured API.

        :param public: endpoint that works without an API key (e.g. costs)
        :param paid: refresh the cached credit balance after a success
        """
        config = self._get_config(company)
        if not config or not config.api_url or (not public and not config._is_configured()):
            return self._result(False, CODE_NOT_CONFIGURED, self._user_message(CODE_NOT_CONFIGURED, ''))

        url = f"{config.api_url.rstrip('/')}/{config.api_version or 'v1'}/{path.lstrip('/')}"
        headers = {'Accept': 'application/json'}
        if config.api_key:
            headers['Authorization'] = f"Bearer {config.api_key}"
        timeout = config.api_delay or 10

        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout:
            _logger.warning("Datacil timeout after %ss on %s", timeout, path)
            return self._result(False, CODE_UNAVAILABLE, _('Datacil did not answer within %s seconds. Please try again.', int(timeout)))
        except requests.exceptions.RequestException as exc:
            _logger.warning("Datacil connection error on %s: %s", path, exc)
            return self._result(False, CODE_UNAVAILABLE, self._user_message(CODE_UNAVAILABLE, ''))

        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {'data': payload}

        status = response.status_code
        api_message = payload.get('message') or response.reason or ''
        if status < 300 and payload.get('success', True):
            data = payload.get('data')
            meta = payload.get('meta') or {}
            if paid:
                self._sync_credits_after_query(config, meta)
            return self._result(True, CODE_OK, api_message, data if data is not None else {}, meta, status)

        code = self._map_status(status, api_message)
        if code == CODE_NO_CREDITS:
            # Balance is stale by definition: force a refresh next time.
            config.sudo().write({'credits_synced_at': False})
        _logger.info("Datacil %s on %s: %s %s", code, path, status, api_message)
        return self._result(False, code, self._user_message(code, api_message, status), status=status)

    @api.model
    def _sync_credits_after_query(self, config, meta):
        """Keep the cached balance close to reality after a paid query."""
        try:
            credits = None
            if isinstance(meta, dict):
                credits = meta.get('credits') or meta.get('balance')
                if isinstance(credits, (int, float)):
                    credits = {'balance': credits}
            if not isinstance(credits, dict):
                result = self._request('usage/credits/', company=config.company)
                credits = result['data'] if result['success'] else None
            if credits:
                config._update_credits_cache(credits)
        except Exception:  # noqa: BLE001 - never break a successful lookup
            _logger.debug("Could not refresh Datacil credits", exc_info=True)

    @api.model
    def _data_path(self, path, company=None):
        config = self._get_config(company)
        country = (config and config.api_country) or 'ecuador'
        return f"{country}/{path}"

    # ------------------------------------------------------------------
    # Identity endpoints
    # ------------------------------------------------------------------
    @api.model
    def lookup_identification(self, identification, company=None):
        """Basic cédula or RUC data (paid)."""
        identification = self.normalize_identification(identification)
        kind = self.identification_kind(identification)
        if not kind:
            return self._result(False, CODE_INVALID, _('You must enter a valid number of digits (10 for ID, 13 for RUC).'))
        result = self._request(self._data_path(f"data/{kind}/{identification}", company), company=company, paid=True)
        result['kind'] = kind
        result['identification'] = identification
        return result

    @api.model
    def get_name(self, identification, company=None):
        """Name / legal name only (free endpoint)."""
        identification = self.normalize_identification(identification)
        if not self.identification_kind(identification):
            return self._result(False, CODE_INVALID, _('You must enter a valid number of digits (10 for ID, 13 for RUC).'))
        return self._request(self._data_path(f"data/name/{identification}", company), company=company)

    @api.model
    def autocomplete_companies(self, query, company=None):
        """Company suggestions by name (free endpoint, min. 3 characters)."""
        query = (query or '').strip()
        if len(query) < 3:
            return self._result(True, CODE_OK, '', [])
        return self._request(self._data_path("data/empresas/autocompletar", company), params={'q': query}, company=company)

    @api.model
    def get_licence(self, cedula, company=None):
        cedula = self.normalize_identification(cedula)
        return self._request(self._data_path(f"data/licence/{cedula}", company), company=company, paid=True)

    @api.model
    def get_vehicle(self, plate, company=None):
        plate = re.sub(r'[^A-Za-z0-9]', '', plate or '').upper()
        if not re.fullmatch(r'[A-Z]{3}\d{3,4}', plate):
            return self._result(False, CODE_INVALID, _('The license plate must have the format AAA000 or AAA0000.'))
        return self._request(self._data_path(f"data/vehiculo/{plate}", company), company=company, paid=True)

    @api.model
    def get_judicial_cases(self, cedula, company=None):
        cedula = self.normalize_identification(cedula)
        return self._request(self._data_path(f"judicial/causas-by-cedula/{cedula}", company), company=company, paid=True)

    @api.model
    def get_ant_citations(self, cedula, company=None):
        cedula = self.normalize_identification(cedula)
        return self._request(self._data_path(f"ant/citaciones/{cedula}", company), company=company, paid=True)

    @api.model
    def get_ant_points(self, cedula, company=None):
        cedula = self.normalize_identification(cedula)
        return self._request(self._data_path(f"ant/puntos/{cedula}", company), company=company, paid=True)

    @api.model
    def get_ant_debt(self, cedula, company=None):
        cedula = self.normalize_identification(cedula)
        return self._request(self._data_path(f"ant/deuda/{cedula}", company), company=company, paid=True)

    @api.model
    def get_company_risk(self, identification, company=None):
        identification = self.normalize_identification(identification)
        return self._request(self._data_path(f"company/{identification}/risk", company), company=company)

    # ------------------------------------------------------------------
    # Usage endpoints
    # ------------------------------------------------------------------
    @api.model
    def get_credits(self, company=None, force=False):
        """Credit balance, served from cache unless stale or ``force``."""
        config = self._get_config(company)
        if config and not force and config._credits_are_fresh():
            return self._result(True, CODE_OK, '', {
                'balance': config.credits_balance,
                'currency': config.credits_currency,
                'synced_at': config.credits_synced_at,
                'cached': True,
            })
        result = self._request('usage/credits/', company=company)
        if result['success'] and config:
            config._update_credits_cache(result['data'])
            result['data'] = dict(result['data'], synced_at=config.credits_synced_at, cached=False)
        return result

    @api.model
    def get_credits_history(self, limit=50, offset=0, company=None):
        return self._request('usage/credits/history', params={'limit': min(int(limit), 50), 'offset': int(offset)}, company=company)

    @api.model
    def get_costs(self, company=None):
        """Endpoint costs (public endpoint). Cached per worker for one hour."""
        config = self._get_config(company)
        key = (self.env.cr.dbname, config.api_url if config else '')
        cached = _COSTS_CACHE.get(key)
        if cached and time.time() - cached[0] < COSTS_CACHE_TTL:
            return dict(cached[1])
        result = self._request('usage/costs/', company=company, public=True)
        if result['success']:
            _COSTS_CACHE[key] = (time.time(), result)
        return result

    @api.model
    def clear_costs_cache(self):
        _COSTS_CACHE.clear()

    @api.model
    def test_connection(self, company=None):
        """Used by the settings "Test connection" button."""
        result = self.get_credits(company=company, force=True)
        if result['success']:
            data = result['data']
            result['message'] = _('Connection OK. Available credits: %s', data.get('balance', 0))
        return result

    # ------------------------------------------------------------------
    # Presentation helpers (shared by the companion modules)
    # ------------------------------------------------------------------
    @api.model
    def pick(self, data, *keys, default=None):
        """Return the first present key of ``data`` (payloads are loosely typed)."""
        if not isinstance(data, dict):
            return default
        for key in keys:
            value = data.get(key)
            if value not in (None, '', [], {}):
                return value
        return default

    @api.model
    def to_web_values(self, model_name, values):
        """Convert ORM values to what ``record.update`` expects in the web client
        (many2one as ``{'id', 'display_name'}``, datetimes as strings)."""
        model = self.env[model_name]
        web_values = {}
        for name, value in values.items():
            field = model._fields.get(name)
            if not field:
                continue
            if field.type == 'many2one':
                if value:
                    record = self.env[field.comodel_name].browse(value)
                    web_values[name] = {'id': record.id, 'display_name': record.display_name}
                else:
                    web_values[name] = False
            elif field.type == 'datetime' and value:
                web_values[name] = fields.Datetime.to_string(value)
            elif field.type == 'date' and value:
                web_values[name] = fields.Date.to_string(value)
            else:
                web_values[name] = value
        return web_values

    @api.model
    def as_list(self, value, *keys):
        """Best-effort list out of a payload block.

        Accepts a list, or a dict holding it under one of ``keys`` (or under
        any key, as a last resort). Payloads are loosely typed: a block may
        come as a list, as ``{'items': [...]}`` or as ``{'total': n}``.
        """
        if isinstance(value, list):
            return value
        if not isinstance(value, dict):
            return []
        found = self.pick(value, *keys, default=None) if keys else None
        if isinstance(found, list):
            return found
        for item in value.values():
            if isinstance(item, list):
                return item
        return []

    @api.model
    def as_count(self, value, *keys):
        """Best-effort count out of a list, a counter dict or a number."""
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for key in ('total', 'count', 'cantidad', 'totalRegistros', 'numero'):
                raw = value.get(key)
                if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                    return int(raw)
            return len(self.as_list(value, *keys))
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    @api.model
    def as_amount(self, value, *keys):
        """Best-effort amount out of a number, a dict or a list of dicts."""
        if isinstance(value, dict):
            value = self.pick(value, *(keys or ('total', 'valor', 'amount', 'monto', 'deuda', 'saldo', 'valorTotal')), default=None)
            if value is None:
                return 0.0
        if isinstance(value, list):
            return sum(self.as_amount(item, *keys) for item in value)
        if isinstance(value, dict):
            return 0.0
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        text = re.sub(r'[^\d,.-]', '', str(value or ''))
        if not text:
            return 0.0
        # Amounts come formatted either way ("1,234.50" or "78,50"): the last
        # separator is the decimal one, the other groups thousands.
        if ',' in text and '.' in text:
            text = text.replace('.', '').replace(',', '.') if text.rfind(',') > text.rfind('.') else text.replace(',', '')
        elif ',' in text:
            head, _sep, tail = text.rpartition(',')
            text = f"{head}.{tail}" if len(tail) in (1, 2) else text.replace(',', '')
        try:
            return float(text)
        except ValueError:
            return 0.0

    @api.model
    def as_text(self, value, *keys):
        """Best-effort label out of a scalar, a dict or a list."""
        if isinstance(value, dict):
            value = self.pick(value, *(keys or ('name', 'nombre', 'descripcion', 'description', 'valor', 'value')), default='')
        if isinstance(value, list):
            return ', '.join(filter(None, (self.as_text(item, *keys) for item in value)))
        if isinstance(value, dict) or value in (None, False, ''):
            return ''
        return str(value).strip()

    # Address blocks come either as a plain street, as a labelled SRI string
    # ("Calle: X Numero: Y Referencia: Z") or as a province/canton/parish path.
    _ADDRESS_LABELS = re.compile(
        r'\b(calle|via|av|numero|n[uú]mero|intersecci[oó]n|interseccion|referencia|barrio|'
        r'ciudadela|urbanizaci[oó]n|urbanizacion|edificio|manzana|lote|conjunto|bloque|piso|oficina)\s*:',
        re.IGNORECASE)

    @api.model
    def parse_address(self, address):
        """Split an address block into ``street``, ``street2``, ``city`` and ``state``.

        ``street`` keeps the way and number, ``street2`` the reference points,
        so both land on the native address fields instead of one long string.
        """
        if not isinstance(address, dict):
            address = {}
        raw_street = self.as_text(self.pick(address, 'street', 'calle', 'direccion', 'dirección'))
        complete = self.as_text(self.pick(address, 'completeAddress', 'direccionCompleta'))
        source = raw_street or complete
        street, street2 = self._split_street(source)
        if not street and complete and complete != source:
            street, street2 = self._split_street(complete)
        return {
            'street': street,
            'street2': street2,
            'city': self.as_text(self.pick(address, 'city', 'ciudad', 'canton', 'cantón', 'parroquia')),
            'state': self.as_text(self.pick(address, 'state', 'provincia')),
            'zip': self.as_text(self.pick(address, 'zip', 'codigoPostal', 'postalCode')),
        }

    @api.model
    def _split_street(self, source):
        if not source:
            return '', ''
        # "GUAYAS/GUAYAQUIL/GUAYAQUIL" is a location path, not a street.
        if '/' in source and not self._ADDRESS_LABELS.search(source):
            return '', ''
        if not self._ADDRESS_LABELS.search(source):
            return source.strip(' ,.-'), ''
        parts = self._ADDRESS_LABELS.split(source)
        blocks, label = {}, None
        for index, chunk in enumerate(parts):
            if index == 0:
                continue
            if index % 2:
                label = chunk.strip().lower()
            elif label:
                value = chunk.strip(' ,.-')
                if value and value.upper() not in ('S/N', 'SN', 'NA', 'N/A'):
                    blocks.setdefault(label, value)
        way = ' '.join(filter(None, [
            blocks.get('calle') or blocks.get('via') or blocks.get('av'),
            blocks.get('numero') or blocks.get('número'),
        ]))
        crossing = blocks.get('interseccion') or blocks.get('intersección')
        if crossing:
            way = f"{way} y {crossing}" if way else crossing
        extra = [blocks[key] for key in (
            'referencia', 'barrio', 'ciudadela', 'urbanizacion', 'urbanización',
            'edificio', 'manzana', 'lote', 'conjunto', 'bloque', 'piso', 'oficina') if blocks.get(key)]
        return way.strip(' ,.-'), ', '.join(extra)

    @api.model
    def format_html(self, data, title=None):
        """Render any JSON payload as a readable (escaped) HTML block.

        Dicts become definition tables, lists become nested lists, scalars are
        printed as-is. Used for chatter notes and result dialogs.
        """
        html = Markup('')
        if title:
            html += Markup('<h5 class="mb-2">%s</h5>') % title
        html += self._format_html_node(data)
        return html

    @api.model
    def _format_html_node(self, node, depth=0):
        if isinstance(node, dict):
            if not node:
                return Markup('<span class="text-muted">-</span>')
            rows = Markup('')
            for key, value in node.items():
                rows += Markup('<tr><th class="pe-3 text-muted fw-normal align-top text-nowrap">%s</th><td>%s</td></tr>') % (
                    self._humanize_key(key), self._format_html_node(value, depth + 1))
            return Markup('<table class="table table-sm table-borderless mb-1"><tbody>%s</tbody></table>') % rows
        if isinstance(node, list):
            if not node:
                return Markup('<span class="text-muted">-</span>')
            if all(not isinstance(item, (dict, list)) for item in node):
                return escape(', '.join(str(item) for item in node))
            items = Markup('').join(Markup('<li class="mb-1">%s</li>') % self._format_html_node(item, depth + 1) for item in node)
            return Markup('<ol class="ps-3 mb-1">%s</ol>') % items
        if node is None or node == '':
            return Markup('<span class="text-muted">-</span>')
        if node is True:
            return escape(_('Yes'))
        if node is False:
            return escape(_('No'))
        return escape(str(node))

    @api.model
    def _humanize_key(self, key):
        key = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', str(key)).replace('_', ' ')
        return key[:1].upper() + key[1:]
