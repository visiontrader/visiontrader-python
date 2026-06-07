"""Options market data client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from visiontrader._http import HttpClient, unwrap_data
from visiontrader.exceptions import SnapshotError
from visiontrader.models import Expiry, OptionsSnapshot, expiry_from_json, snapshot_from_json

def _format_date(value: date) -> str:
    return value.isoformat()


def _format_ts(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.isoformat().replace("+00:00", "Z")


class VisionOptionsClient:
    """
    Client for the VisionTrader Options REST API (VT.AspNetApp).

    Query parameter for the board symbol is ``symbol`` (e.g. BTC, BTC_USDC).
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._http = HttpClient(base_url, timeout=timeout, client=client)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> VisionOptionsClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def list_exchanges(self) -> list[str]:
        """GET /exchanges?type=options — exchanges that provide options data."""
        body = self._http.get_json("/exchanges", params={"type": "options"})
        return list(unwrap_data(body))

    def list_instruments(self, exchange: str) -> list[str]:
        """GET options/instruments."""
        body = self._http.get_json(
            "options/instruments",
            params={"exchange": exchange},
        )
        return list(unwrap_data(body))

    def list_expiries(self, exchange: str, symbol: str) -> list[Expiry]:
        """GET options/expiries."""
        body = self._http.get_json(
            "options/expiries",
            params={"exchange": exchange, "symbol": symbol},
        )
        return [expiry_from_json(item) for item in unwrap_data(body)]

    def list_dates(self, exchange: str, symbol: str, expiry: date) -> list[date]:
        """GET options/dates."""
        body = self._http.get_json(
            "options/dates",
            params={
                "exchange": exchange,
                "symbol": symbol,
                "expiry": _format_date(expiry),
            },
        )
        return [date.fromisoformat(d) for d in unwrap_data(body)]

    def get_snapshot(
        self,
        exchange: str,
        symbol: str,
        *,
        expiry: date,
        ts: datetime,
        resolution: str = "1m",
    ) -> OptionsSnapshot:
        """GET /options/snapshot."""
        body = self._http.get_json(
            "/options/snapshot",
            params={
                "exchange": exchange,
                "symbol": symbol,
                "expiry": _format_date(expiry),
                "ts": _format_ts(ts),
                "resolution": resolution,
            },
        )
        raw = unwrap_data(body)
        if raw is None:
            raise SnapshotError("Empty snapshot data")
        return snapshot_from_json(raw)

    def get_snapshots(
        self,
        exchange: str,
        symbol: str,
        *,
        expiry: date,
        on_date: date,
        resolution: str = "1m",
    ) -> list[OptionsSnapshot]:
        """GET /options/snapshots."""
        body = self._http.get_json(
            "/options/snapshots",
            params={
                "exchange": exchange,
                "symbol": symbol,
                "expiry": _format_date(expiry),
                "date": _format_date(on_date),
                "resolution": resolution,
            },
        )
        items = unwrap_data(body) or []
        return [snapshot_from_json(item) for item in items]

    def snapshots_to_dataframe(
        self,
        exchange: str,
        symbol: str,
        *,
        expiry: date,
        on_date: date,
        resolution: str = "1m",
    ) -> pd.DataFrame:
        """Load a day's snapshots as a long-format DataFrame."""
        snapshots = self.get_snapshots(
            exchange,
            symbol,
            expiry=expiry,
            on_date=on_date,
            resolution=resolution,
        )
        rows: list[dict[str, Any]] = []
        for snap in snapshots:
            for leg in snap.options:
                rows.append(
                    {
                        "exchange": snap.exchange,
                        "underlying": snap.underlying,
                        "expiry": snap.expiry,
                        "ts": snap.ts,
                        "underlying_price": snap.underlying_price,
                        "symbol": leg.symbol,
                        "strike": leg.strike,
                        "type": leg.type,
                        "bid": leg.bid,
                        "ask": leg.ask,
                        "mark_price": leg.mark_price,
                        "mark_iv": leg.mark_iv,
                        "oi": leg.oi,
                    }
                )
        return pd.DataFrame(rows)
