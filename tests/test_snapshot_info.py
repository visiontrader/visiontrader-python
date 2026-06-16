from datetime import date, datetime, timezone

import pandas as pd
import pytest

from visiontrader.models import (
    format_board_expiry_label,
    format_board_name,
    format_time_to_expiry_duration,
    time_to_expiry_years,
)
from visiontrader.options import VisionOptionsClient


def test_format_board_expiry_label() -> None:
    assert format_board_expiry_label('BTC-19JUN26-67000-C') == '19Jun26'
    assert format_board_expiry_label('BTC-4JUN26-67000-C') == '4Jun26'


def test_format_board_name() -> None:
    assert format_board_name('BTC', 'BTC-19JUN26-67000-C') == 'BTC - 19Jun26'


def test_time_to_expiry_years_uses_365_25_day_year() -> None:
    ts = datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)
    expiry = date(2026, 6, 19)
    assert time_to_expiry_years(ts, expiry) == pytest.approx(30 / 365.25, rel=1e-6)


def test_format_time_to_expiry_duration() -> None:
    ts = datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)
    expiry = date(2026, 6, 19)
    assert format_time_to_expiry_duration(ts, expiry) == '30 days'


def test_info_snapshot_builds_card() -> None:
    snap = pd.DataFrame(
        {
            'exchange': ['deribit'] * 5,
            'underlying': ['BTC'] * 5,
            'expiry': [date(2026, 6, 19)] * 5,
            'ts': [datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)] * 5,
            'underlyingPrice': [67000.0] * 5,
            'symbol': [f'BTC-19JUN26-{strike}-C' for strike in [65000, 66000, 67000, 68000, 69000]],
            'strike': [65000.0, 66000.0, 67000.0, 68000.0, 69000.0],
            'moneyness': [65000 / 67000, 66000 / 67000, 1.0, 68000 / 67000, 69000 / 67000],
            'type': ['call'] * 5,
            'markIv': [0.55, 0.52, 0.51, 0.52, 0.55],
        }
    )
    info = VisionOptionsClient().info_snapshot(snap)
    assert info.board_name == 'BTC - 19Jun26'
    assert info.exchange == 'Deribit'
    assert info.expiry_display == '2026.06.19'
    assert info.time_to_expiry == '30 days'
    assert info.time_to_expiry_years == pytest.approx(30 / 365.25, rel=1e-6)
    assert info.underlying_price == 67000.0
    assert info.implied_forward_price == pytest.approx(67000.0, rel=1e-2)
    assert info.mark_iv == 0.51
    assert 'Time to expiry: 30 days' in str(info)
    assert 'Implied forward price (smile anchor): 67 000.00' in str(info)
