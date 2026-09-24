from contextlib import contextmanager
from unittest.mock import patch

import requests

from odoo.tests import TransactionCase

REQUESTS_GET = 'odoo.addons.datacil_client_odoo.models.datacil_api.requests.get'

CEDULA_PAYLOAD = {
    'status': 200, 'success': True, 'message': 'Cedula found', 'timestamp': 1,
    'data': {
        'id': '1710034065',
        'name': 'MARTINEZ SILVA ANDREA LUCIA',
        'firstname': 'ANDREA LUCIA',
        'lastname': 'MARTINEZ SILVA',
        'gender': 'female',
        'birthDate': '1990-05-15',
        'address': {'state': 'GUAYAS', 'canton': 'GUAYAQUIL', 'city': 'GUAYAQUIL', 'street': 'AV. 9 DE OCTUBRE 123',
                    'completeAddress': 'GUAYAS/GUAYAQUIL/GUAYAQUIL'},
        'elapsed': {'years': 36, 'months': 4, 'days': 7, 'totalDays': 13277, 'iso': 'P36Y4M7D', 'text': '36 años 4 meses 7 días'},
        'contact': {'email': 'andrea@example.com', 'phone': '042345678', 'cellphone': '0991234567'},
    },
    'meta': {},
}

RUC_PAYLOAD = {
    'status': 200, 'success': True, 'message': 'RUC found', 'timestamp': 1,
    'data': {
        'id': '1790016919001',
        'name': 'DISTRIBUIDORA COMERCIAL DEL PACIFICO S.A.',
        'status': {'code': 'suspended', 'isGhost': False, 'hasNonexistentTransactions': False, 'isCanceled': False, 'cancelationReason': None},
        'profile': {'type': 'company', 'regime': 'general', 'category': None, 'specialContributor': True,
                    'accountingRequired': True, 'withholdingAgent': False},
        'activity': {'main': 'COMERCIO AL POR MAYOR', 'startDate': '2020-01-15', 'endDate': None},
        'legalRepresentatives': [{'id': '0923456789', 'name': 'LOPEZ RAMIREZ CARLOS'}],
        'address': {'state': 'PICHINCHA', 'canton': 'QUITO', 'city': 'QUITO',
                    'street': 'Calle: AV. PRINCIPAL Numero: S24-456 Interseccion: CALLE SECUNDARIA Referencia: FRENTE AL PARQUE',
                    'completeAddress': 'AV. PRINCIPAL S24-456 Y CALLE SECUNDARIA'},
        'contact': {'email': 'info@pacifico.com', 'phone': '022345678', 'cellphone': None},
    },
    'meta': {},
}

CREDITS_PAYLOAD = {'status': 200, 'success': True, 'message': 'ok', 'timestamp': 1, 'data': {'balance': 120, 'currency': 'credits'}}
COSTS_PAYLOAD = {'status': 200, 'success': True, 'message': 'ok', 'timestamp': 1,
                 'data': {'costs': [{'serviceKey': 'ec.cedula', 'cost': 8, 'countryCode': 'ec', 'description': 'Cedula'}]}}
HISTORY_PAYLOAD = {'status': 200, 'success': True, 'message': 'ok', 'timestamp': 1,
                   'data': {'transactions': [{'$id': '1', '$createdAt': '2026-01-01T10:00:00.000Z', 'service_key': 'ec.cedula',
                                              'query_param': '1710034065', 'amount': -8}]}}


class FakeResponse:
    def __init__(self, status_code=200, payload=None, reason='OK'):
        self.status_code = status_code
        self._payload = payload
        self.reason = reason

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


class DatacilTestCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.config = cls.env['datacil.config']._get_or_create_for_company(cls.company)
        cls.config.write({
            'api_url': 'https://api-test.datacil.com',
            'api_key': 'sk_test',
            'api_version': 'v1',
            'api_country': 'ecuador',
            'api_delay': 5,
            'load_created_partners': True,
            'credits_synced_at': False,
        })
        cls.api = cls.env['datacil.api']
        cls.env['datacil.api'].clear_costs_cache()

    def free_vat(self, *vats):
        """Detach an identification from any pre-existing partner.

        Tests run against real databases too, where a contact may already carry
        the identification used by the fixtures (the SRI final consumer, for
        instance). Rolled back with the test transaction.
        """
        partners = self.env['res.partner'].with_context(active_test=False).search([('vat', 'in', list(vats))])
        if partners:
            partners.write({'vat': False})

    @contextmanager
    def mock_get(self, responses):
        """``responses``: list of FakeResponse/Exception consumed in order, or a callable(url, **kw)."""
        calls = []

        def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            if callable(responses):
                result = responses(url, **kwargs)
            else:
                result = responses[min(len(calls) - 1, len(responses) - 1)]
            if isinstance(result, Exception):
                raise result
            return result

        with patch(REQUESTS_GET, side_effect=fake_get):
            yield calls

    @staticmethod
    def ok(payload):
        return FakeResponse(200, payload)

    @staticmethod
    def error(status, message='error'):
        return FakeResponse(status, {'status': status, 'success': False, 'message': message, 'timestamp': 1}, reason=message)

    @staticmethod
    def timeout():
        return requests.exceptions.Timeout()

    @staticmethod
    def connection_error():
        return requests.exceptions.ConnectionError()
