"""Options market data client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx
import pandas as pd

from visiontrader._http import HttpClient, unwrap_data
from visiontrader.exceptions import SnapshotError
from visiontrader.models import OptionsSnapshot, expiry_from_json, snapshot_from_json


EXPIRY_COLUMNS = ['expiry', 'settlement_period']
DATES_COLUMN = 'available dates'
SNAPSHOT_COLUMNS = [
    'exchange',
    'underlying',
    'expiry',
    'ts',
    'underlyingPrice',
    'symbol',
    'strike',
    'type',
    'bid',
    'ask',
    'markPrice',
    'markIv',
    'oi',
]


def _coerce_date(value: date | str) -> date:
    if isinstance(value, str):
        return date.fromisoformat(value)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _format_date(value: date | str) -> str:
    return _coerce_date(value).isoformat()


def _format_ts(value: datetime | str) -> str:
    ts = _coerce_datetime(value)
    if ts.tzinfo is None:
        return ts.isoformat() + 'Z'
    return ts.isoformat().replace('+00:00', 'Z')


def _snapshot_to_dataframe(snapshot: OptionsSnapshot) -> pd.DataFrame:
    if not snapshot.options:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    return pd.DataFrame(
        [
            {
                'exchange': snapshot.exchange,
                'underlying': snapshot.underlying,
                'expiry': snapshot.expiry,
                'ts': snapshot.ts,
                'underlyingPrice': snapshot.underlying_price,
                'symbol': leg.symbol,
                'strike': leg.strike,
                'type': leg.type,
                'bid': leg.bid,
                'ask': leg.ask,
                'markPrice': leg.mark_price,
                'markIv': leg.mark_iv,
                'oi': leg.oi,
            }
            for leg in snapshot.options
        ],
        columns=SNAPSHOT_COLUMNS,
    )


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
        body = self._http.get_json('/exchanges', params={'type': 'options'})
        return list(unwrap_data(body))

    def list_instruments(self, exchange: str) -> list[str]:
        """GET options/instruments."""
        body = self._http.get_json(
            'options/instruments',
            params={'exchange': exchange},
        )
        return list(unwrap_data(body))

    def list_expiries(self, exchange: str, symbol: str) -> pd.DataFrame:
        """GET options/expiries — columns: ``expiry``, ``settlement_period``."""
        body = self._http.get_json(
            'options/expiries',
            params={'exchange': exchange, 'symbol': symbol},
        )
        items = [expiry_from_json(item) for item in unwrap_data(body)]
        return pd.DataFrame(
            [{'expiry': e.expiry, 'settlement_period': e.settlement_period} for e in items],
            columns=EXPIRY_COLUMNS,
        )

    def list_dates(self, exchange: str, symbol: str, expiry: date | str) -> pd.DataFrame:
        """GET options/dates — column: ``available dates``."""
        body = self._http.get_json(
            'options/dates',
            params={
                'exchange': exchange,
                'symbol': symbol,
                'expiry': _format_date(expiry),
            },
        )
        dates = [date.fromisoformat(d) for d in unwrap_data(body)]
        return pd.DataFrame({DATES_COLUMN: dates})

    def get_snapshot(
        self,
        exchange: str,
        symbol: str,
        expiry: date | str,
        ts: datetime | str,
        *,
        resolution: str = '1m',
    ) -> pd.DataFrame:
        """GET /options/snapshot — returns an options board as a DataFrame.

        ``expiry``: ``yyyy-MM-dd`` string or :class:`datetime.date`.
        ``ts``: RFC3339 string (e.g. ``2026-04-25T12:00`` or ``...Z``) or :class:`datetime.datetime`.

        Columns: ``exchange``, ``underlying``, ``expiry``, ``ts``, ``underlyingPrice``,
        then per-leg ``symbol``, ``strike``, ``type``, ``bid``, ``ask``, ``markPrice``, ``markIv``, ``oi``.
        """
        body = self._http.get_json(
            '/options/snapshot',
            params={
                'exchange': exchange,
                'symbol': symbol,
                'expiry': _format_date(expiry),
                'ts': _format_ts(ts),
                'resolution': resolution,
            },
        )
        raw = unwrap_data(body)
        if raw is None:
            raise SnapshotError('Empty snapshot data')
        return _snapshot_to_dataframe(snapshot_from_json(raw))

    def get_snapshots(
        self,
        exchange: str,
        symbol: str,
        expiry: date | str,
        on_date: date | str,
        *,
        resolution: str = '1m',
    ) -> list[OptionsSnapshot]:
        """GET /options/snapshots."""
        body = self._http.get_json(
            '/options/snapshots',
            params={
                'exchange': exchange,
                'symbol': symbol,
                'expiry': _format_date(expiry),
                'date': _format_date(on_date),
                'resolution': resolution,
            },
        )
        items = unwrap_data(body) or []
        return [snapshot_from_json(item) for item in items]

    def snapshots_to_dataframe(
        self,
        exchange: str,
        symbol: str,
        expiry: date | str,
        on_date: date | str,
        *,
        resolution: str = '1m',
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
                        'exchange': snap.exchange,
                        'underlying': snap.underlying,
                        'expiry': snap.expiry,
                        'ts': snap.ts,
                        'underlying_price': snap.underlying_price,
                        'symbol': leg.symbol,
                        'strike': leg.strike,
                        'type': leg.type,
                        'bid': leg.bid,
                        'ask': leg.ask,
                        'mark_price': leg.mark_price,
                        'mark_iv': leg.mark_iv,
                        'oi': leg.oi,
                    }
                )
        return pd.DataFrame(rows)
