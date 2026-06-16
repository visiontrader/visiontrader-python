"""Response models for the VisionTrader Options API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Literal

OptionType = Literal['call', 'put']

DERIBIT_EXPIRY_HOUR_UTC = 8
DAYS_PER_YEAR = 365.25
_BOARD_EXPIRY_RE = re.compile(r'^(\d+)([A-Za-z]+)(\d+)$')


@dataclass(frozen=True, slots=True)
class Expiry:
    expiry: date
    settlement_period: str | None


@dataclass(frozen=True, slots=True)
class OptionLeg:
    symbol: str
    strike: float
    type: OptionType
    bid: float | None
    ask: float | None
    mark_price: float | None
    mark_iv: float | None
    oi: float | None


@dataclass(frozen=True, slots=True)
class OptionsSnapshot:
    exchange: str
    underlying: str
    expiry: date
    ts: datetime
    underlying_price: float | None
    options: tuple[OptionLeg, ...]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SnapshotInfo:
    """Summary card for a snapshot board DataFrame."""

    board_name: str
    exchange: str
    expiry: date
    ts: datetime
    time_to_expiry: str
    time_to_expiry_years: float
    underlying_price: float | None
    implied_forward_price: float | None
    mark_iv: float | None

    @property
    def expiry_display(self) -> str:
        return self.expiry.strftime('%Y.%m.%d')

    def __str__(self) -> str:
        underlying = 'n/a' if self.underlying_price is None else f'{self.underlying_price:,.2f}'.replace(',', ' ')
        implied_forward = (
            'n/a'
            if self.implied_forward_price is None
            else f'{self.implied_forward_price:,.2f}'.replace(',', ' ')
        )
        mark_iv = 'n/a' if self.mark_iv is None else f'{self.mark_iv:.4f}'
        ts_utc = self.ts if self.ts.tzinfo is not None else self.ts.replace(tzinfo=timezone.utc)
        ts_text = ts_utc.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        return (
            f'Board: {self.board_name}\n'
            f'Exchange: {self.exchange}\n'
            f'Expiration: {self.expiry_display}\n'
            f'Snapshot time: {ts_text}\n'
            f'Time to expiry: {self.time_to_expiry}\n'
            f'Time to expiry (years): {self.time_to_expiry_years:.6f}\n'
            f'Underlying price: {underlying}\n'
            f'Implied forward price (smile anchor): {implied_forward}\n'
            f'Mark IV (ATM): {mark_iv}'
        )


def format_board_expiry_label(symbol: str) -> str:
    part = str(symbol).split('-')[1]
    match = _BOARD_EXPIRY_RE.match(part)
    if match is None:
        return part
    day, month, year = match.groups()
    return f'{day}{month.title()}{year}'


def format_board_name(underlying: str, symbol: str) -> str:
    return f'{underlying} - {format_board_expiry_label(symbol)}'


def expiry_datetime_utc(expiry: date, *, hour_utc: int = DERIBIT_EXPIRY_HOUR_UTC) -> datetime:
    return datetime.combine(expiry, time(hour_utc), tzinfo=timezone.utc)


def time_to_expiry_years(ts: datetime, expiry: date, *, days_per_year: float = DAYS_PER_YEAR) -> float:
    ts_utc = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    ts_utc = ts_utc.astimezone(timezone.utc)
    expiry_utc = expiry_datetime_utc(expiry)
    return (expiry_utc - ts_utc).total_seconds() / (days_per_year * 86400)


def format_time_to_expiry_duration(ts: datetime, expiry: date) -> str:
    ts_utc = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    ts_utc = ts_utc.astimezone(timezone.utc)
    expiry_utc = expiry_datetime_utc(expiry)
    total_seconds = int((expiry_utc - ts_utc).total_seconds())
    if total_seconds < 0:
        return 'expired'

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f'{days} day' if days == 1 else f'{days} days')
    if hours:
        parts.append(f'{hours} hour' if hours == 1 else f'{hours} hours')
    if minutes and not days:
        parts.append(f'{minutes} minute' if minutes == 1 else f'{minutes} minutes')
    if not parts:
        return 'less than 1 minute'
    return ', '.join(parts)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def expiry_from_json(item: dict[str, Any]) -> Expiry:
    period = item.get('settlement_period')
    return Expiry(
        expiry=_parse_date(item['expiry']),
        settlement_period=None if period in (None, '') else str(period),
    )


def option_leg_from_json(item: dict[str, Any]) -> OptionLeg:
    return OptionLeg(
        symbol=item['symbol'],
        strike=float(item['strike']),
        type=item['type'],
        bid=item.get('bid'),
        ask=item.get('ask'),
        mark_price=item.get('markPrice'),
        mark_iv=item.get('markIv'),
        oi=item.get('oi'),
    )


def snapshot_from_json(payload: dict[str, Any]) -> OptionsSnapshot:
    return OptionsSnapshot(
        exchange=payload['exchange'],
        underlying=payload['underlying'],
        expiry=_parse_date(payload['expiry']),
        ts=_parse_ts(payload['ts']),
        underlying_price=payload.get('underlyingPrice'),
        options=tuple(option_leg_from_json(o) for o in payload.get('options', [])),
    )
