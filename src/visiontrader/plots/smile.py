"""Volatility smile plots."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


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


def _format_underlying_px(value: float) -> str:
    return f'{round(value):,}'.replace(',', ' ')


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


WATERMARK_TEXT = 'visiontrader.io'
WATERMARK_FONTSIZE = 7
WATERMARK_COLOR = '#8cb4d9'
WATERMARK_ALPHA = 0.35


def _set_smile_watermark(ax: Axes) -> None:
    ax.text(
        0.99,
        0.01,
        WATERMARK_TEXT,
        transform=ax.transAxes,
        ha='right',
        va='bottom',
        fontsize=WATERMARK_FONTSIZE,
        color=WATERMARK_COLOR,
        alpha=WATERMARK_ALPHA,
    )


def _set_smile_titles(ax: Axes, smile: pd.DataFrame) -> None:
    main, subtitle = _smile_title_parts(smile)
    ax.text(0.5, 1.08, main, transform=ax.transAxes, ha='center', va='bottom', fontsize=11)
    ax.text(
        0.5,
        1.01,
        subtitle,
        transform=ax.transAxes,
        ha='center',
        va='bottom',
        fontsize=8,
        color='#555555',
    )


def plot_smile(smile: pd.DataFrame) -> tuple[Figure, Axes]:
    """Plot a volatility smile in a Jupyter notebook and return ``(fig, ax)``.

    With the usual ``%matplotlib inline`` backend the figure is shown once at
    cell end. In other environments ``display(fig)`` or ``plt.show()`` is used.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            'plot_smile requires matplotlib. Install with: pip install "visiontrader[plots]"',
        ) from exc

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(smile['moneyness'], smile['markIv'], 'o-', label='mark IV', markersize=4)
    ax.axvline(1.0, color='red', linestyle='--', linewidth=0.8)
    ax.set_xlabel('moneyness')
    ax.set_ylabel('mark IV')
    ax.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.subplots_adjust(top=0.78)
    _set_smile_titles(ax, smile)
    _set_smile_watermark(ax)

    if _in_ipython() and _uses_inline_backend():
        pass
    elif _in_ipython():
        from IPython.display import display

        display(fig)
    else:
        plt.show()

    return fig, ax
