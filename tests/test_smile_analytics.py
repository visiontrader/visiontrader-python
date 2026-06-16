import math

import pandas as pd
import pytest

from visiontrader.options import VisionOptionsClient
from visiontrader.smile_analytics import ImpliedForwardPrice, implied_forward_price_from_smile


def _client() -> VisionOptionsClient:
    return VisionOptionsClient(base_url='http://test')


def _synthetic_smile(
    *,
    anchor: float = 67_000.0,
    underlying_price: float = 66_500.0,
) -> pd.DataFrame:
    strikes = [65_000.0, 66_000.0, 67_000.0, 68_000.0, 69_000.0]
    log_anchor = math.log(anchor)
    rows = []
    for strike in strikes:
        mark_iv = 0.5 + 2.0 * (math.log(strike) - log_anchor) ** 2
        rows.append(
            {
                'strike': strike,
                'markIv': mark_iv,
                'underlyingPrice': underlying_price,
                'type': 'call',
            }
        )
    return pd.DataFrame(rows)


def test_implied_forward_price_finds_quadratic_anchor() -> None:
    smile = _synthetic_smile(anchor=67_123.0, underlying_price=66_500.0)
    result = implied_forward_price_from_smile(smile)
    assert isinstance(result, ImpliedForwardPrice)
    assert result.price == pytest.approx(67_123.0, rel=1e-3)
    assert result.mark_iv == pytest.approx(0.5, rel=1e-3)
    assert result.snapshot_underlying_price == 66_500.0
    assert result.delta_vs_snapshot == pytest.approx(623.0, rel=1e-3)


def test_implied_forward_price_client_wrapper() -> None:
    smile = _synthetic_smile()
    result = _client().implied_forward_price(smile)
    assert result.price == pytest.approx(67_000.0, rel=1e-3)


def test_implied_forward_price_requires_three_strikes() -> None:
    smile = pd.DataFrame(
        {
            'strike': [66_000.0, 67_000.0],
            'markIv': [0.52, 0.50],
        }
    )
    with pytest.raises(ValueError, match='at least 3 distinct strikes'):
        implied_forward_price_from_smile(smile)


def test_implied_forward_price_str() -> None:
    smile = _synthetic_smile(anchor=67_000.0, underlying_price=66_948.82)
    text = str(implied_forward_price_from_smile(smile))
    assert 'Implied forward price (smile anchor):' in text
    assert 'Snapshot underlying: 66 948.82' in text
