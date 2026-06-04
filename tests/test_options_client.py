from datetime import date, datetime, timezone

import httpx
import pytest

from visiontrader import OptionsClient
from visiontrader.exceptions import ValidationError


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/exchanges":
            return httpx.Response(200, json={"data": ["deribit"]})
        if request.url.path.endswith("/instruments"):
            return httpx.Response(200, json={"data": ["BTC", "BTC_USDC"]})
        if request.url.path.endswith("/expiries"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"expiry": "2026-05-01", "settlement_period": "monthly"},
                    ]
                },
            )
        if request.url.path.endswith("/dates"):
            return httpx.Response(200, json={"data": ["2026-04-25"]})
        if request.url.path == "/options/snapshot":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "exchange": "deribit",
                        "underlying": "BTC",
                        "expiry": "2026-05-01",
                        "ts": "2026-04-25T12:00:00Z",
                        "underlyingPrice": 77000.0,
                        "options": [
                            {
                                "symbol": "BTC-1MAY26-70000-C",
                                "strike": 70000,
                                "type": "call",
                                "bid": 0.07,
                                "ask": 0.12,
                                "markPrice": 0.1,
                                "markIv": 0.48,
                                "oi": 100.0,
                            }
                        ],
                    },
                    "error": None,
                },
            )
        if request.url.path == "/options/snapshots":
            return httpx.Response(200, json={"data": [], "error": None})
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


def test_list_exchanges() -> None:
    http = httpx.Client(transport=_mock_transport())
    with OptionsClient(client=http) as client:
        assert client.list_exchanges(type="options") == ["deribit"]


def test_list_instruments_and_expiries() -> None:
    http = httpx.Client(transport=_mock_transport())
    with OptionsClient(client=http) as client:
        assert client.list_instruments("deribit") == ["BTC", "BTC_USDC"]
        expiries = client.list_expiries("deribit", "BTC")
        assert expiries[0].expiry == date(2026, 5, 1)
        assert expiries[0].settlement_period == "monthly"


def test_get_snapshot() -> None:
    http = httpx.Client(transport=_mock_transport())
    with OptionsClient(client=http) as client:
        snap = client.get_snapshot(
            "deribit",
            "BTC",
            expiry=date(2026, 5, 1),
            ts=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        )
        assert snap.underlying == "BTC"
        assert len(snap.options) == 1
        assert snap.options[0].mark_iv == 0.48


def test_validation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad symbol", "code": -1})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with OptionsClient(client=http) as client:
        with pytest.raises(ValidationError, match="bad symbol"):
            client.list_instruments("deribit")
