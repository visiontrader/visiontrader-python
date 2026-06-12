"""Volatility smile plots."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

import pandas as pd

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

SmileMetricName = Literal['oi', 'spread', 'askbid']
WithMetricsInput = str | Sequence[str]

SMILE_METRICS: frozenset[str] = frozenset({'oi', 'spread', 'askbid'})
PANEL_METRICS: frozenset[str] = frozenset({'oi', 'spread'})
BID_POINT_COLOR = '#357FD3'
ASK_POINT_COLOR = '#E63232'
POINT_SIZE = 5
MAIN_LEGEND_FONTSIZE = 20 / 3  # ~1.5× smaller than matplotlib default legend (~10pt)
FIG_WIDTH = 8.0
MAIN_PANEL_HEIGHT = 3.5
METRIC_PANEL_HEIGHT = 1.0

WATERMARK_TEXT = 'www.visiontrader.io'
WATERMARK_FONTSIZE = 8
WATERMARK_COLOR = 'gray'
WATERMARK_ALPHA = 0.6


def _in_ipython() -> bool:
    try:
        from IPython import get_ipython

        return get_ipython() is not None
    except ImportError:
        return False


def _uses_inline_backend() -> bool:
    import matplotlib

    backend = matplotlib.get_backend().lower()
    return 'inline' in backend or 'ipympl' in backend


def parse_with_metrics(value: WithMetricsInput | None) -> list[str]:
    """Normalize ``with_metrics`` input to an ordered list of metric names."""
    if value is None:
        return []

    if isinstance(value, str):
        items = [part.strip() for part in value.split('|')] if '|' in value else [value]
    else:
        items = list(value)

    if not items:
        return []

    metrics: list[str] = []
    for item in items:
        metric = str(item).strip().lower()
        if not metric:
            raise ValueError('with_metrics contains an empty metric name')
        if metric not in SMILE_METRICS:
            raise ValueError(f'Unknown smile metric: {item!r}')
        if metric in metrics:
            raise ValueError(f'Duplicate smile metric: {item!r}')
        metrics.append(metric)
    return metrics


def _format_underlying_px(value: float) -> str:
    return f'{round(value):,}'.replace(',', ' ')


def _moneyness_reference_price(smile: pd.DataFrame) -> float | None:
    if smile.empty:
        return None
    row = smile.iloc[0]
    if 'moneynessUnderlyingPrice' in smile.columns:
        px = row.get('moneynessUnderlyingPrice')
        if px is not None and not pd.isna(px):
            return float(px)
    px = row.get('underlyingPrice')
    if px is not None and not pd.isna(px):
        return float(px)
    return None


def _add_strike_secondary_xaxis(ax: Axes, underlying_px: float) -> None:
    from matplotlib.ticker import FuncFormatter

    def moneyness_to_strike(moneyness: float) -> float:
        return moneyness * underlying_px

    def strike_to_moneyness(strike: float) -> float:
        return strike / underlying_px

    secax = ax.secondary_xaxis('top', functions=(moneyness_to_strike, strike_to_moneyness))
    secax.set_xlabel('strike')
    secax.xaxis.set_major_formatter(
        FuncFormatter(lambda strike, _pos: _format_underlying_px(strike)),
    )


def _smile_title_parts(smile: pd.DataFrame) -> tuple[str, str]:
    if smile.empty:
        raise ValueError('smile DataFrame is empty')

    row = smile.iloc[0]
    underlying = row['underlying']
    exchange = str(row['exchange']).capitalize()
    expiry_label = str(row['symbol']).split('-')[1]
    ts = pd.Timestamp(row['ts'])
    if ts.tzinfo is not None:
        ts = ts.tz_convert('UTC')
    else:
        ts = ts.tz_localize('UTC')
    ts_label = ts.strftime('%Y-%m-%d %H:%M')
    main = f'{underlying} vol smile {exchange} - {expiry_label} @ {ts_label}'

    subtitle_parts: list[str] = []
    period = row.get('settlement_period')
    if period is not None and not pd.isna(period):
        subtitle_parts.append(f'period = {period}')
    option_type = row.get('type')
    if option_type is not None and not pd.isna(option_type):
        subtitle_parts.append(f'type = {option_type}')
    if 'moneynessUnderlyingPrice' in smile.columns:
        px = row['moneynessUnderlyingPrice']
    else:
        px = row.get('underlyingPrice')
    if px is not None and not pd.isna(px):
        subtitle_parts.append(f'underlying px = {_format_underlying_px(float(px))}')
    subtitle = f'[{", ".join(subtitle_parts)}]'
    return main, subtitle


def _set_smile_titles(ax: Axes, smile: pd.DataFrame) -> None:
    main, subtitle = _smile_title_parts(smile)
    ax.text(0.5, 1.28, main, transform=ax.transAxes, ha='center', va='bottom', fontsize=11)
    ax.text(
        0.5,
        1.21,
        subtitle,
        transform=ax.transAxes,
        ha='center',
        va='bottom',
        fontsize=8,
        color='#555555',
    )


def _set_figure_watermark(fig: Figure) -> None:
    fig.text(
        0.99,
        0.01,
        WATERMARK_TEXT,
        transform=fig.transFigure,
        ha='right',
        va='bottom',
        fontsize=WATERMARK_FONTSIZE,
        color=WATERMARK_COLOR,
        alpha=WATERMARK_ALPHA,
    )


def _scaled_quote_iv(price: pd.Series, mark_price: pd.Series, mark_iv: pd.Series) -> pd.Series:
    return price * mark_iv / mark_price


def _plot_askbid_overlay(ax: Axes, smile: pd.DataFrame) -> None:
    base = smile.dropna(subset=['markPrice', 'markIv'])
    base = base[base['markPrice'] != 0]

    bid = base.dropna(subset=['bid'])
    if not bid.empty:
        bid_iv = _scaled_quote_iv(bid['bid'], bid['markPrice'], bid['markIv'])
        ax.scatter(
            bid['moneyness'],
            bid_iv,
            s=POINT_SIZE,
            marker='^',
            color=BID_POINT_COLOR,
            alpha=0.8,
            label='bid IV (scaled)',
            zorder=3,
        )

    ask = base.dropna(subset=['ask'])
    if not ask.empty:
        ask_iv = _scaled_quote_iv(ask['ask'], ask['markPrice'], ask['markIv'])
        ax.scatter(
            ask['moneyness'],
            ask_iv,
            s=POINT_SIZE,
            marker='v',
            color=ASK_POINT_COLOR,
            alpha=0.8,
            label='ask IV (scaled)',
            zorder=3,
        )


def _metric_bar_width(moneyness: pd.Series) -> float:
    values = pd.Series(moneyness.dropna().unique()).sort_values()
    if len(values) < 2:
        return 0.01
    return float(values.diff().dropna().min()) * 0.8


def _plot_smile_main(ax: Axes, smile: pd.DataFrame, *, show_xlabel: bool, show_askbid: bool) -> None:
    ax.plot(smile['moneyness'], smile['markIv'], 'o-', label='mark IV', markersize=4)
    if show_askbid:
        _plot_askbid_overlay(ax, smile)
    ax.axvline(1.0, color='red', linestyle='--', linewidth=0.8)
    if show_xlabel:
        ax.set_xlabel('moneyness')
    ax.set_ylabel('mark IV')
    ax.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.4)
    underlying_px = _moneyness_reference_price(smile)
    if underlying_px is not None and underlying_px != 0:
        _add_strike_secondary_xaxis(ax, underlying_px)
    ax.legend(loc='lower left', fontsize=MAIN_LEGEND_FONTSIZE)


def _plot_oi_metric(ax: Axes, smile: pd.DataFrame) -> None:
    valid = smile.dropna(subset=['oi'])
    if not valid.empty:
        width = _metric_bar_width(valid['moneyness'])
        ax.bar(valid['moneyness'], valid['oi'], width=width, color='tab:blue', alpha=0.7)
    ax.set_ylabel('oi')
    ax.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.4)


def _plot_spread_metric(ax: Axes, smile: pd.DataFrame) -> None:
    spread = smile['ask'] - smile['bid']
    valid = smile.loc[spread.notna()].copy()
    if not valid.empty:
        width = _metric_bar_width(valid['moneyness'])
        ax.bar(
            valid['moneyness'],
            spread.loc[spread.notna()],
            width=width,
            color='tab:orange',
            alpha=0.7,
        )
    ax.set_ylabel('spread')
    ax.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.4)


def _plot_metric_panel(ax: Axes, smile: pd.DataFrame, metric: str) -> None:
    if metric == 'oi':
        _plot_oi_metric(ax, smile)
    elif metric == 'spread':
        _plot_spread_metric(ax, smile)


def _show_figure(fig: Figure) -> None:
    if _in_ipython() and _uses_inline_backend():
        return
    if _in_ipython():
        from IPython.display import display

        display(fig)
        return
    import matplotlib.pyplot as plt

    plt.show()


def plot_smile(
    smile: pd.DataFrame,
    with_metrics: WithMetricsInput | None = None,
) -> tuple[Figure, Axes] | tuple[Figure, list[Axes]]:
    """Plot a volatility smile in a Jupyter notebook.

    Expects a smile-ready DataFrame (typically from ``filter_for_smile``).

    ``with_metrics`` accepts ``'oi'``, ``['oi', 'spread']``, ``'oi|askbid'``, and
    similar forms. ``oi`` and ``spread`` add bar-chart panels below the smile;
    ``askbid`` overlays bid/ask IV points on the main chart. The main panel also
    shows a top ``strike`` axis (matplotlib ``secondary_xaxis``) when underlying
    price is available. Returns ``(fig, ax)``
    or ``(fig, axes)`` when panel metrics are present.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            'plot_smile requires matplotlib. Install with: pip install "visiontrader[plots]"',
        ) from exc

    metrics = parse_with_metrics(with_metrics)
    panel_metrics = [metric for metric in metrics if metric in PANEL_METRICS]
    show_askbid = 'askbid' in metrics
    panel_count = len(panel_metrics)

    if panel_count == 0:
        fig, ax = plt.subplots(figsize=(FIG_WIDTH, MAIN_PANEL_HEIGHT))
        axes = [ax]
    else:
        total_height = MAIN_PANEL_HEIGHT + panel_count * METRIC_PANEL_HEIGHT
        fig, axes = plt.subplots(
            1 + panel_count,
            1,
            sharex=True,
            figsize=(FIG_WIDTH, total_height),
            gridspec_kw={'height_ratios': [MAIN_PANEL_HEIGHT] + [METRIC_PANEL_HEIGHT] * panel_count},
        )
        axes = list(axes)

    main_ax = axes[0]
    _plot_smile_main(main_ax, smile, show_xlabel=panel_count == 0, show_askbid=show_askbid)

    for metric_ax, metric in zip(axes[1:], panel_metrics, strict=True):
        _plot_metric_panel(metric_ax, smile, metric)

    if panel_count > 0:
        axes[-1].set_xlabel('moneyness')

    fig.tight_layout()
    fig.subplots_adjust(top=0.82 if panel_count == 0 else 0.92)
    _set_smile_titles(main_ax, smile)
    _set_figure_watermark(fig)
    _show_figure(fig)

    if panel_count == 0:
        return fig, main_ax
    return fig, axes
