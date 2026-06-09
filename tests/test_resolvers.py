from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from visiontrader.exceptions import ValidationError
from visiontrader.resolvers import (
    parse_relative_ts,
    resolve_expiry,
    resolve_next_expiry,
    resolve_ts,
    utc_tomorrow,
)


def test_utc_tomorrow() -> None:
    assert utc_tomorrow(reference_date=date(2026, 6, 9)) == date(2026, 6, 10)


def test_resolve_next_expiry_picks_nearest_on_or_after_tomorrow() -> None:
    expiries = pd.DataFrame(
        {
            'expiry': [
                date(2026, 6, 9),
                date(2026, 6, 10),
                date(2026, 6, 11),
                date(2026, 6, 12),
            ],
            'settlement_period': ['day', 'day', 'day', 'week'],
        }
    )
    resolved = resolve_next_expiry(
        expiries,
        'day',
        reference_date=date(2026, 6, 9),
    )
    assert resolved == date(2026, 6, 10)


def test_resolve_expiry_next_daily_alias() -> None:
    expiries = pd.DataFrame(
        {
            'expiry': [date(2026, 6, 10), date(2026, 6, 11)],
            'settlement_period': ['day', 'day'],
        }
    )
    resolved = resolve_expiry(
        'next_daily',
        expiries,
        reference_date=date(2026, 6, 9),
    )
    assert resolved == date(2026, 6, 10)


def test_resolve_expiry_iso_date() -> None:
    expiries = pd.DataFrame(columns=['expiry', 'settlement_period'])
    assert resolve_expiry('2026-06-04', expiries) == date(2026, 6, 4)


def test_resolve_next_expiry_empty_raises() -> None:
    expiries = pd.DataFrame(
        {
            'expiry': [date(2026, 6, 9)],
            'settlement_period': ['day'],
        }
    )
    with pytest.raises(ValidationError, match='No'):
        resolve_next_expiry(expiries, 'day', reference_date=date(2026, 6, 9))


@pytest.mark.parametrize(
    ('value', 'minutes'),
    [
        ('-4m', 4),
        ('-4M', 4),
        ('-1h', 60),
        ('-1H', 60),
        ('-1d', 24 * 60),
        ('-1D', 24 * 60),
    ],
)
def test_parse_relative_ts(value: str, minutes: int) -> None:
    now = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)
    resolved = parse_relative_ts(value, now=now)
    assert resolved == now - timedelta(minutes=minutes)


def test_resolve_ts_rejects_unsigned_offset() -> None:
    with pytest.raises(ValidationError, match='Forward relative'):
        resolve_ts('15m')


def test_resolve_ts_rejects_seconds() -> None:
    with pytest.raises(ValidationError, match='seconds not supported'):
        resolve_ts('-30s')
