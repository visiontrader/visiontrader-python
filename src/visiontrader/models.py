"""Response models for the VisionTrader Options API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

OptionType = Literal['call', 'put']


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
