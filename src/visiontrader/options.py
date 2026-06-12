"""Options market data client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

import httpx
import pandas as pd

from visiontrader._http import DEFAULT_TIMEOUT, HttpClient, unwrap_data
from visiontrader.exceptions import SnapshotError
from visiontrader.models import OptionsSnapshot, expiry_from_json, snapshot_from_json
from visiontrader.resolvers import is_expiry_alias, resolve_expiry, resolve_ts


EXPIRY_COLUMNS = ['expiry', 'settlement_period']
DATES_COLUMN = 'available dates'
SNAPSHOT_COLUMNS = [
    'exchange',
    'underlying',
    'expiry',
    'settlement_period',
    'ts',
    'underlyingPrice',
    'symbol',
    'strike',
    'moneyness',
    'type',
    'bid',
    'ask',
    'markPrice',
    'markIv',
    'oi',
]
OptionType = Literal['call', 'put']
DEFAULT_EXCHANGE = 'deribit'


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


def _leg_moneyness(strike: float, underlying_price: float | None) -> float | None:
    if underlying_price is None or underlying_price == 0:
        return None
    return strike / underlying_price


def _settlement_period_from_expiries(
    expiries: pd.DataFrame,
    expiry: date,
) -> str | None:
    matched = expiries.loc[expiries['expiry'] == expiry, 'settlement_period']
    if matched.empty:
        return None
    value = matched.iloc[0]
    if value is None or pd.isna(value):
        return None
    return str(value)


def _snapshot_to_dataframe(
    snapshot: OptionsSnapshot,
    *,
    settlement_period: str | None = None,
) -> pd.DataFrame:
    if not snapshot.options:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    return pd.DataFrame(
        [
            {
                'exchange': snapshot.exchange,
                'underlying': snapshot.underlying,
                'expiry': snapshot.expiry,
                'settlement_period': settlement_period,
                'ts': snapshot.ts,
                'underlyingPrice': snapshot.underlying_price,
                'symbol': leg.symbol,
                'strike': leg.strike,
                'moneyness': _leg_moneyness(leg.strike, snapshot.underlying_price),
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

    Query parameter for the board instrument is ``instrument`` (e.g. BTC, BTC_USDC).

    HTTP requests use a default ``timeout`` of 240 seconds (4 minutes); pass a
    lower value to ``VisionOptionsClient(timeout=...)`` if needed.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
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

    def list_expiries(
        self,
        exchange: str,
        instrument: str,
        *,
        tradeable_only: bool | None = None,
    ) -> pd.DataFrame:
        """GET options/expiries — columns: ``expiry``, ``settlement_period``.

        ``tradeable_only``: when set, passes ``tradeableOnly`` to the API to return
        only boards that are still tradeable.
        """
        params: dict[str, str | bool] = {
            'exchange': exchange,
            'instrument': instrument,
        }
        if tradeable_only is not None:
            params['tradeableOnly'] = tradeable_only
        body = self._http.get_json('options/expiries', params=params)
        items = [expiry_from_json(item) for item in unwrap_data(body)]
        return pd.DataFrame(
            [{'expiry': e.expiry, 'settlement_period': e.settlement_period} for e in items],
            columns=EXPIRY_COLUMNS,
        )

    def list_dates(self, exchange: str, instrument: str, expiry: date | str) -> pd.DataFrame:
        """GET options/dates — column: ``available dates``."""
        body = self._http.get_json(
            'options/dates',
            params={
                'exchange': exchange,
                'instrument': instrument,
                'expiry': _format_date(expiry),
            },
        )
        dates = [date.fromisoformat(d) for d in unwrap_data(body)]
        return pd.DataFrame({DATES_COLUMN: dates})

    def _resolve_snapshot_expiry(
        self,
        exchange: str,
        instrument: str,
        expiry: date | str,
    ) -> tuple[date, str | None]:
        if isinstance(expiry, str) and is_expiry_alias(expiry):
            expiries = self.list_expiries(exchange, instrument, tradeable_only=True)
            resolved = resolve_expiry(expiry, expiries)
            return resolved, _settlement_period_from_expiries(expiries, resolved)

        resolved = _coerce_date(expiry)
        expiries = self.list_expiries(exchange, instrument)
        return resolved, _settlement_period_from_expiries(expiries, resolved)

    def get_snapshot(
        self,
        instrument: str,
        expiry: date | str,
        ts: datetime | str,
        *,
        exchange: str = DEFAULT_EXCHANGE,
        resolution: str = '1m',
    ) -> pd.DataFrame:
        """GET /options/snapshot — returns an options board as a DataFrame.

        ``exchange`` defaults to ``deribit``.
        ``expiry``: ``yyyy-MM-dd``, :class:`datetime.date`, or an alias such as
        ``next_daily`` / ``next_weekly`` / ``next_monthly`` / ``next_quarterly``.
        ``ts``: RFC3339 string, :class:`datetime.datetime`, or a relative offset
        such as ``-4m``, ``-1h``, ``-1d`` (UTC, backward only).

        Columns: ``exchange``, ``underlying``, ``expiry``, ``settlement_period``, ``ts``,
        ``underlyingPrice``, then per-leg ``symbol``, ``strike``, ``moneyness``, ``type``,
        ``bid``, ``ask``, ``markPrice``, ``markIv``, ``oi``. ``moneyness`` is
        ``strike / underlyingPrice``.
        """
        resolved_expiry, settlement_period = self._resolve_snapshot_expiry(
            exchange,
            instrument,
            expiry,
        )
        resolved_ts = resolve_ts(ts)
        body = self._http.get_json(
            '/options/snapshot',
            params={
                'exchange': exchange,
                'instrument': instrument,
                'expiry': _format_date(resolved_expiry),
                'ts': _format_ts(resolved_ts),
                'resolution': resolution,
            },
        )
        raw = unwrap_data(body)
        if raw is None:
            raise SnapshotError('Empty snapshot data')
        return _snapshot_to_dataframe(
            snapshot_from_json(raw),
            settlement_period=settlement_period,
        )

    def filter_for_smile(
        self,
        snap: pd.DataFrame,
        option_type: OptionType,
        min_moneyness: float | None = None,
        max_moneyness: float | None = None,
        *,
        underlying_price: float | None = None,
    ) -> pd.DataFrame:
        """Filter a snapshot board into a smile-ready DataFrame (sorted by moneyness).

        Keeps one ``option_type``, drops rows without ``markIv``. Moneyness bounds
        apply only when ``min_moneyness`` and/or ``max_moneyness`` are passed
        explicitly. When ``underlying_price`` is set, ``moneyness`` is recomputed as
        ``strike / underlying_price`` instead of the snapshot value.
        """
        smile = snap.loc[snap['type'] == option_type].dropna(subset=['markIv']).copy()
        if underlying_price is not None:
            if underlying_price == 0:
                raise ValueError('underlying_price must not be zero')
            smile['moneyness'] = smile['strike'] / underlying_price
            smile['moneynessUnderlyingPrice'] = underlying_price
        if min_moneyness is not None:
            smile = smile.loc[smile['moneyness'] >= min_moneyness]
        if max_moneyness is not None:
            smile = smile.loc[smile['moneyness'] <= max_moneyness]
        return smile.sort_values('moneyness').reset_index(drop=True)

    def get_snapshots(
        self,
        exchange: str,
        instrument: str,
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
                'instrument': instrument,
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
        instrument: str,
        expiry: date | str,
        on_date: date | str,
        *,
        resolution: str = '1m',
    ) -> pd.DataFrame:
        """Load a day's snapshots as a long-format DataFrame."""
        snapshots = self.get_snapshots(
            exchange,
            instrument,
            expiry=expiry,
            on_date=on_date,
            resolution=resolution,
        )
        if not snapshots:
            return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
        return pd.concat(
            [_snapshot_to_dataframe(snapshot) for snapshot in snapshots],
            ignore_index=True,
        )
