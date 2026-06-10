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


def _smile_title(smile: pd.DataFrame) -> str:
    if smile.empty:
        raise ValueError('smile DataFrame is empty')

    row = smile.iloc[0]
    underlying = row['underlying']
    exchange = str(row['exchange']).capitalize()
    expiry_label = str(row['symbol']).split('-')[1]
    meta: list[str] = []
    period = row.get('settlement_period')
    if period is not None and not pd.isna(period):
        meta.append(str(period))
    option_type = row.get('type')
    if option_type is not None and not pd.isna(option_type):
        meta.append(str(option_type))
    meta_part = f' [{", ".join(meta)}]' if meta else ''
    ts = pd.Timestamp(row['ts'])
    if ts.tzinfo is not None:
        ts = ts.tz_convert('UTC')
    else:
        ts = ts.tz_localize('UTC')
    ts_label = ts.strftime('%Y-%m-%d %H:%M')
    return f'{underlying} vol smile {exchange} - {expiry_label}{meta_part} @ {ts_label}'


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
    ax.set_title(_smile_title(smile), fontsize=10)
    ax.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.4)
    ax.legend()
    fig.tight_layout()

    if _in_ipython() and _uses_inline_backend():
        pass
    elif _in_ipython():
        from IPython.display import display

        display(fig)
    else:
        plt.show()

    return fig, ax
