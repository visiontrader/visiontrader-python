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
            'exchange': ['deribit'],
            'underlying': ['BTC'],
            'expiry': [date(2026, 6, 19)],
            'ts': [datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)],
            'underlyingPrice': [67000.0],
            'symbol': ['BTC-19JUN26-67000-C'],
            'strike': [67000.0],
            'moneyness': [1.0],
            'type': ['call'],
            'markIv': [0.51],
        }
    )
    info = VisionOptionsClient().info_snapshot(snap)
    assert info.board_name == 'BTC - 19Jun26'
    assert info.exchange == 'Deribit'
    assert info.expiry_display == '2026.06.19'
    assert info.time_to_expiry == '30 days'
    assert info.time_to_expiry_years == pytest.approx(30 / 365.25, rel=1e-6)
    assert info.underlying_price == 67000.0
    assert info.mark_iv == 0.51
    assert 'Time to expiry: 30 days' in str(info)
