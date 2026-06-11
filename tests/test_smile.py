from datetime import date, datetime, timezone

import httpx
import matplotlib
import pandas as pd
import pytest

matplotlib.use('Agg')

from visiontrader import VisionOptionsClient
from visiontrader.plots import plot_smile
from visiontrader.plots.smile import _smile_title_parts


def _sample_snapshot() -> pd.DataFrame:
    return pd.DataFrame(
        {
            'symbol': ['C-66000', 'P-66000', 'C-67000', 'P-67000', 'C-70000'],
            'strike': [66000, 66000, 67000, 67000, 70000],
            'moneyness': [0.98, 0.98, 1.0, 1.0, 1.15],
            'type': ['call', 'put', 'call', 'put', 'call'],
            'markIv': [0.57, 0.57, 0.51, 0.51, None],
        }
    )


def _client() -> VisionOptionsClient:
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    return VisionOptionsClient(client=httpx.Client(transport=transport))


def test_get_smile_filters_and_sorts() -> None:
    smile = _client().get_smile(_sample_snapshot(), 'call', 0.99, 1.02)
    assert list(smile['strike']) == [67000]
    assert smile.iloc[0]['markIv'] == 0.51


def test_get_smile_without_bounds_returns_all_legs() -> None:
    snap = pd.DataFrame(
        {
            'symbol': ['C-low', 'C-mid', 'C-high'],
            'strike': [1, 2, 3],
            'moneyness': [0.89, 1.0, 1.14],
            'type': ['call', 'call', 'call'],
            'markIv': [0.3, 0.48, 0.5],
        }
    )
    smile = _client().get_smile(snap, 'call')
    assert list(smile['moneyness']) == [0.89, 1.0, 1.14]


def test_get_smile_recomputes_moneyness_with_underlying_price() -> None:
    snap = pd.DataFrame(
        {
            'strike': [66000, 67000],
            'moneyness': [0.98, 1.0],
            'underlyingPrice': [67346.0, 67346.0],
            'type': ['call', 'call'],
            'markIv': [0.5, 0.48],
        }
    )
    smile = _client().get_smile(snap, 'call', underlying_price=66000)
    assert smile.iloc[0]['moneyness'] == pytest.approx(1.0)
    assert smile.iloc[1]['moneyness'] == pytest.approx(67000 / 66000)


def test_get_smile_includes_boundary_moneyness() -> None:
    snap = pd.DataFrame(
        {
            'symbol': ['C-low', 'C-high'],
            'strike': [1, 2],
            'moneyness': [0.9, 1.13],
            'type': ['call', 'call'],
            'markIv': [0.4, 0.5],
        }
    )
    smile = _client().get_smile(snap, 'call', 0.9, 1.13)
    assert len(smile) == 2
    assert smile.iloc[0]['moneyness'] == 0.9
    assert smile.iloc[1]['moneyness'] == 1.13


def _plot_smile_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            'underlying': ['BTC', 'BTC', 'BTC'],
            'exchange': ['deribit', 'deribit', 'deribit'],
            'symbol': ['BTC-4JUN26-67000-C', 'BTC-4JUN26-67000-C', 'BTC-4JUN26-67000-C'],
            'settlement_period': ['month', 'month', 'month'],
            'type': ['call', 'call', 'call'],
            'underlyingPrice': [66948.82, 66948.82, 66948.82],
            'ts': [pd.Timestamp('2026-06-03 12:00:00+00:00')] * 3,
            'moneyness': [0.95, 1.0, 1.05],
            'markIv': [0.5, 0.48, 0.46],
        }
    )


def test_plot_smile_returns_fig_and_ax() -> None:
    fig, ax = plot_smile(_plot_smile_sample())
    assert fig is not None
    assert ax is not None
    import matplotlib.pyplot as plt

    plt.close(fig)


def test_plot_smile_watermark() -> None:
    _, ax = plot_smile(_plot_smile_sample())
    watermark = [t for t in ax.texts if t.get_text() == 'visiontrader.io']
    assert len(watermark) == 1
    assert watermark[0].get_fontsize() == 8
    assert watermark[0].get_alpha() == 0.6
    assert watermark[0].get_color() == 'gray'
    import matplotlib.pyplot as plt

    plt.close(ax.figure)


def test_smile_title_parts() -> None:
    main, subtitle = _smile_title_parts(_plot_smile_sample())
    assert main == 'BTC vol smile Deribit - 4JUN26 @ 2026-06-03 12:00'
    assert subtitle == '[period = month, type = call, underlying px = 66 949]'


def test_smile_title_parts_uses_custom_underlying_price() -> None:
    smile = _client().get_smile(
        pd.DataFrame(
            {
                'underlying': ['BTC'],
                'exchange': ['deribit'],
                'symbol': ['BTC-4JUN26-67000-C'],
                'settlement_period': ['day'],
                'type': ['call'],
                'underlyingPrice': [66948.82],
                'strike': [67000],
                'moneyness': [1.0],
                'ts': [pd.Timestamp('2026-06-10 16:08:00+00:00')],
                'markIv': [0.5],
            }
        ),
        'call',
        underlying_price=66000,
    )
    main, subtitle = _smile_title_parts(smile)
    assert main == 'BTC vol smile Deribit - 4JUN26 @ 2026-06-10 16:08'
    assert subtitle == '[period = day, type = call, underlying px = 66 000]'


def test_get_snapshot_uses_instrument_query_param() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/expiries'):
            return httpx.Response(200, json={'data': []})
        if request.url.path == '/options/snapshot':
            seen.update(dict(request.url.params))
            return httpx.Response(
                200,
                json={
                    'data': {
                        'exchange': 'deribit',
                        'underlying': 'BTC',
                        'expiry': '2026-05-01',
                        'ts': '2026-04-25T12:00:00Z',
                        'underlyingPrice': 77000.0,
                        'options': [],
                    },
                    'error': None,
                },
            )
        return httpx.Response(404)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with VisionOptionsClient(client=http) as client:
        client.get_snapshot(
            'BTC',
            '2026-05-01',
            datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        )
    assert seen['instrument'] == 'BTC'
    assert 'symbol' not in seen
