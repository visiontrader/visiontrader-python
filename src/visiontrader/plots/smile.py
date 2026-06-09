"""Volatility smile plots."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


def PlotSmile(smile: pd.DataFrame) -> tuple[Figure, Axes]:
    """Plot a volatility smile in a Jupyter notebook and return ``(fig, ax)``."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            'PlotSmile requires matplotlib. Install with: pip install "visiontrader[plots]"',
        ) from exc

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(smile['moneyness'], smile['markIv'], 'o-', label='mark IV', markersize=4)
    ax.axvline(1.0, color='red', linestyle='--', linewidth=0.8)
    ax.set_xlabel('moneyness')
    ax.set_ylabel('mark IV')
    ax.grid(True, which='major', linestyle='-', linewidth=0.5, alpha=0.4)
    ax.legend()
    fig.tight_layout()

    try:
        from IPython.display import display

        display(fig)
    except ImportError:
        plt.show()

    return fig, ax
