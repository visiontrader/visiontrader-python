from datetime import date, datetime, timezone

import httpx
import matplotlib
import pandas as pd
import pytest

matplotlib.use('Agg')

from visiontrader import VisionOptionsClient
from visiontrader.plots import PlotSmile


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


def test_get_smile_default_bounds() -> None:
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
    assert list(smile['moneyness']) == [1.0]


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


def test_plot_smile_returns_fig_and_ax() -> None:
    smile = pd.DataFrame({'moneyness': [0.95, 1.0, 1.05], 'markIv': [0.5, 0.48, 0.46]})
    fig, ax = PlotSmile(smile)
    assert fig is not None
    assert ax is not None
    import matplotlib.pyplot as plt

    plt.close(fig)


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
