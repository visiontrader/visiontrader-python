"""Analytics helpers for volatility smile DataFrames."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class ImpliedForwardPrice:
    """Forward price implied by the minimum of a fitted volatility smile."""

    price: float
    mark_iv: float
    snapshot_underlying_price: float | None

    @property
    def delta_vs_snapshot(self) -> float | None:
        if self.snapshot_underlying_price is None:
            return None
        return self.price - self.snapshot_underlying_price

    def __str__(self) -> str:
        price = f'{self.price:,.2f}'.replace(',', ' ')
        mark_iv = f'{self.mark_iv:.4f}'
        if self.snapshot_underlying_price is None:
            snapshot = 'n/a'
            delta = 'n/a'
        else:
            snapshot = f'{self.snapshot_underlying_price:,.2f}'.replace(',', ' ')
            delta_value = self.delta_vs_snapshot
            delta = 'n/a' if delta_value is None else f'{delta_value:+,.2f}'.replace(',', ' ')
        return (
            f'Implied forward price (smile anchor): {price}\n'
            f'Mark IV at anchor: {mark_iv}\n'
            f'Snapshot underlying: {snapshot}\n'
            f'Delta vs snapshot: {delta}'
        )


def _snapshot_underlying_price(smile: pd.DataFrame) -> float | None:
    if smile.empty or 'underlyingPrice' not in smile.columns:
        return None
    value = smile.iloc[0]['underlyingPrice']
    if value is None or pd.isna(value):
        return None
    return float(value)


def _strikes_with_mark_iv(smile: pd.DataFrame) -> pd.DataFrame:
    frame = smile.dropna(subset=['strike', 'markIv']).copy()
    if frame.empty:
        raise ValueError('smile DataFrame has no rows with markIv')
    grouped = (
        frame.groupby('strike', as_index=False)['markIv']
        .mean()
        .sort_values('strike')
        .reset_index(drop=True)
    )
    if len(grouped) < 3:
        raise ValueError('smile DataFrame needs at least 3 distinct strikes with markIv')
    return grouped


def _quadratic_minimum(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    coeffs = np.polyfit(x, y, 2)
    a, b, c = (float(value) for value in coeffs)
    if a <= 0:
        idx = int(np.argmin(y))
        return float(x[idx]), float(y[idx])
    x_min = -b / (2 * a)
    y_min = a * x_min * x_min + b * x_min + c
    return x_min, y_min


def implied_forward_price_from_smile(smile: pd.DataFrame) -> ImpliedForwardPrice:
    """Estimate the forward price from the minimum of a quadratic smile fit.

    Fits ``markIv`` as a quadratic in ``log(strike)``, finds the analytic
    minimum, and maps it back to a strike price. The result is the price level
    the market smile is centered on — which may differ from ``underlyingPrice``
    in the snapshot (e.g. index vs dated future).
    """
    curve = _strikes_with_mark_iv(smile)
    log_strikes = np.log(curve['strike'].to_numpy(dtype=float))
    mark_iv = curve['markIv'].to_numpy(dtype=float)
    log_price, iv_min = _quadratic_minimum(log_strikes, mark_iv)
    return ImpliedForwardPrice(
        price=math.exp(log_price),
        mark_iv=iv_min,
        snapshot_underlying_price=_snapshot_underlying_price(smile),
    )
