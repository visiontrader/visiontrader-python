from datetime import date, datetime, timezone

import httpx
import pytest

from visiontrader import VisionOptionsClient
from visiontrader.exceptions import ApiError, ValidationError


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/exchanges':
            return httpx.Response(200, json={'data': ['deribit']})
        if request.url.path.endswith('/instruments'):
            return httpx.Response(200, json={'data': ['BTC', 'BTC_USDC']})
        if request.url.path.endswith('/expiries'):
            return httpx.Response(
                200,
                json={
                    'data': [
                        {'expiry': '2026-05-01', 'settlement_period': 'monthly'},
                    ]
                },
            )
        if request.url.path.endswith('/dates'):
            return httpx.Response(200, json={'data': ['2026-04-25']})
        if request.url.path == '/options/snapshot':
            return httpx.Response(
                200,
                json={
                    'data': {
                        'exchange': 'deribit',
                        'underlying': 'BTC',
                        'expiry': '2026-05-01',
                        'ts': '2026-04-25T12:00:00Z',
                        'underlyingPrice': 77000.0,
                        'options': [
                            {
                                'symbol': 'BTC-1MAY26-70000-C',
                                'strike': 70000,
                                'type': 'call',
                                'bid': 0.07,
                                'ask': 0.12,
                                'markPrice': 0.1,
                                'markIv': 0.48,
                                'oi': 100.0,
                            }
                        ],
                    },
                    'error': None,
                },
            )
        if request.url.path == '/options/snapshots':
            return httpx.Response(200, json={'data': [], 'error': None})
        return httpx.Response(404, json={'error': 'not found'})

    return httpx.MockTransport(handler)


def test_list_exchanges() -> None:
    http = httpx.Client(transport=_mock_transport())
    with VisionOptionsClient(client=http) as vision_options:
        assert vision_options.list_exchanges() == ['deribit']


def test_list_instruments_and_expiries() -> None:
    http = httpx.Client(transport=_mock_transport())
    with VisionOptionsClient(client=http) as vision_options:
        assert vision_options.list_instruments('deribit') == ['BTC', 'BTC_USDC']
        expiries = vision_options.list_expiries('deribit', 'BTC')
        assert expiries[0].expiry == date(2026, 5, 1)
        assert expiries[0].settlement_period == 'monthly'


def test_get_snapshot() -> None:
    http = httpx.Client(transport=_mock_transport())
    with VisionOptionsClient(client=http) as vision_options:
        snap = vision_options.get_snapshot(
            'deribit',
            'BTC',
            date(2026, 5, 1),
            datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        )
        assert list(snap.columns) == [
            'symbol', 'strike', 'type', 'bid', 'ask', 'markPrice', 'markIv', 'oi',
        ]
        assert len(snap) == 1
        assert snap.iloc[0]['symbol'] == 'BTC-1MAY26-70000-C'
        assert snap.iloc[0]['markIv'] == 0.48


def test_get_snapshot_string_args() -> None:
    http = httpx.Client(transport=_mock_transport())
    with VisionOptionsClient(client=http) as vision_options:
        snap = vision_options.get_snapshot(
            'deribit',
            'BTC',
            '2026-05-01',
            '2026-04-25T12:00:00Z',
        )
        assert len(snap) == 1
        assert snap.iloc[0]['symbol'] == 'BTC-1MAY26-70000-C'


def test_validation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={'error': 'bad symbol', 'code': -1})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with VisionOptionsClient(client=http) as vision_options:
        with pytest.raises(ValidationError, match='bad symbol') as exc_info:
            vision_options.list_instruments('deribit')
        assert exc_info.value.code == -1


def test_response_error_in_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={'data': None, 'error': 'snapshot not found', 'code': -2},
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with VisionOptionsClient(client=http) as vision_options:
        with pytest.raises(ApiError, match='snapshot not found') as exc_info:
            vision_options.list_exchanges()
        assert exc_info.value.code == -2


def test_missing_data_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'error': None})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with VisionOptionsClient(client=http) as vision_options:
        with pytest.raises(ApiError, match="Response missing 'data' field"):
            vision_options.list_exchanges()
