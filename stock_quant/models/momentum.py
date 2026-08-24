from __future__ import annotations

import numpy as np
import pandas as pd


def tsm_score(df: pd.DataFrame) -> pd.Series:
    """Cross-section-neutralized time-series momentum score in [-100, 100]."""
    r20 = df["return_20d"]
    r60 = df["return_60d"]
    acceleration = r20 - r60 / 3.0
    raw = 0.6 * r20 + 0.4 * acceleration
    return 100.0 * np.tanh(raw / 0.20)


def mean_reversion_score(df: pd.DataFrame) -> pd.Series:
    """Short-term stretch score; negative when price is extended above its mean."""
    z = df["close_z_20d"]
    return -100.0 * np.tanh(z / 2.0)


def range_expansion_score(df: pd.DataFrame) -> pd.Series:
    """Score based on current range relative to its recent history."""
    range20 = df["range_20d"]
    z = range20.groupby(df["symbol"]).transform(
        lambda s: (s - s.rolling(60).mean()) / s.rolling(60).std(ddof=0)
    )
    return 100.0 * np.tanh(z / 2.0)
