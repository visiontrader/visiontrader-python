"""Resolve semantic aliases for expiry and timestamp arguments."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from visiontrader.exceptions import ValidationError

EXPIRY_ALIASES: dict[str, str] = {
    'next_daily': 'day',
    'next_weekly': 'week',
    'next_monthly': 'month',
    'next_quarterly': 'quarter',
}

_RELATIVE_TS_RE = re.compile(r'^-(\d+)([mhd])$', re.IGNORECASE)
_UNSIGNED_RELATIVE_TS_RE = re.compile(r'^\d+[mhd]$', re.IGNORECASE)


def is_expiry_alias(value: str) -> bool:
    return value in EXPIRY_ALIASES


def is_relative_ts(value: str) -> bool:
    return _RELATIVE_TS_RE.match(value) is not None


def utc_tomorrow(*, reference_date: date | None = None) -> date:
    today = reference_date or datetime.now(timezone.utc).date()
    return today + timedelta(days=1)


def resolve_next_expiry(
    expiries: pd.DataFrame,
    settlement_period: str,
    *,
    reference_date: date | None = None,
) -> date:
    """Nearest live board expiry for tomorrow UTC and the given settlement period."""
    tomorrow = utc_tomorrow(reference_date=reference_date)
    filtered = expiries.loc[
        (expiries['settlement_period'] == settlement_period) & (expiries['expiry'] >= tomorrow)
    ].sort_values('expiry')
    if filtered.empty:
        raise ValidationError(
            f'No {settlement_period!r} expiry on or after {tomorrow.isoformat()}',
        )
    resolved = filtered.iloc[0]['expiry']
    if isinstance(resolved, pd.Timestamp):
        return resolved.date()
    if isinstance(resolved, datetime):
        return resolved.date()
    return resolved


def resolve_expiry(
    value: date | str,
    expiries: pd.DataFrame,
    *,
    reference_date: date | None = None,
) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return pd.Timestamp(value).date()

    if is_expiry_alias(value):
        return resolve_next_expiry(
            expiries,
            EXPIRY_ALIASES[value],
            reference_date=reference_date,
        )

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f'Unknown expiry alias or date: {value!r}') from exc


def parse_relative_ts(value: str, *, now: datetime | None = None) -> datetime:
    match = _RELATIVE_TS_RE.match(value)
    if match is None:
        raise ValidationError(
            f'Relative timestamp must match -<n>m|h|d (e.g. -4m, -1h, -1d), got {value!r}',
        )

    amount = int(match.group(1))
    unit = match.group(2).lower()
    anchor = now or datetime.now(timezone.utc)

    if unit == 'm':
        return anchor - timedelta(minutes=amount)
    if unit == 'h':
        return anchor - timedelta(hours=amount)
    return anchor - timedelta(days=amount)


def resolve_ts(value: datetime | str, *, now: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValidationError(f'Unsupported timestamp type: {type(value).__name__}')

    if is_relative_ts(value):
        return parse_relative_ts(value, now=now)

    if _UNSIGNED_RELATIVE_TS_RE.match(value):
        raise ValidationError(
            f'Forward relative timestamps are not supported, got {value!r}',
        )

    if value and value[0] == '-' and not is_relative_ts(value):
        raise ValidationError(
            f'Unsupported relative timestamp {value!r}; use -<n>m|h|d (seconds not supported)',
        )

    return datetime.fromisoformat(value.replace('Z', '+00:00'))
