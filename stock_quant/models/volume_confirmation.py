"""Volume confirmation layer for Momentum and Range Expansion signals.

This module provides volume analysis as a confirmation layer, not as a voting signal.
It helps interpret whether momentum and range expansion are backed by volume conviction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def volume_trend(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Detect volume trend direction: increasing or decreasing relative to its 20-day mean.

    Returns:
        Series with values:
        - 1.0: volume accelerating (above mean)
        - 0.0: volume neutral (around mean)
        - -1.0: volume decelerating (below mean)
    """
    vol = df.get("volume", pd.Series(np.nan, index=df.index))
    vol_mean = df.get("volume_mean_20d", pd.Series(np.nan, index=df.index))

    if vol.isna().all() or vol_mean.isna().all():
        return pd.Series(0.0, index=df.index)

    # Normalized: how far current volume from its mean
    relative = vol / vol_mean.replace(0, np.nan)

    trend = pd.Series(0.0, index=df.index, dtype=float)
    trend.loc[relative > 1.1] = 1.0
    trend.loc[relative < 0.9] = -1.0

    return trend


def momentum_volume_alignment(df: pd.DataFrame) -> pd.Series:
    """Check if price momentum aligns with volume trend.

    Returns True when:
    - Price going up (20d return > 0) AND volume accelerating
    - Price going down (20d return < 0) AND volume decelerating

    Returns False when momentum/volume diverge.
    """
    ret_20d = df.get("return_20d", pd.Series(np.nan, index=df.index))
    vol_trend = volume_trend(df)

    aligned = pd.Series(False, index=df.index, dtype=bool)

    # Both up
    aligned.loc[(ret_20d > 0) & (vol_trend > 0.5)] = True
    # Both down
    aligned.loc[(ret_20d < 0) & (vol_trend < -0.5)] = True

    return aligned


def breakout_volume_confirmation(df: pd.DataFrame, threshold: float = 1.2) -> pd.Series:
    """Check if range expansion (price breakout) is confirmed by volume.

    A range expansion is considered confirmed if:
    - Current volume is above 1.2x the 20-day mean

    Args:
        threshold: Multiple of 20-day volume mean to consider as confirmation

    Returns:
        Boolean Series: True if range expansion has volume confirmation
    """
    relative_vol = df.get("relative_volume_20d", pd.Series(np.nan, index=df.index))
    exp_score = df.get("exp_score", pd.Series(np.nan, index=df.index))

    # Expansion score > 25 means significant range expansion
    expanding = exp_score > 25.0
    vol_confirmed = relative_vol > threshold

    return expanding & vol_confirmed


def price_volume_divergence(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """Detect price-volume divergence: price moves but volume doesn't follow.

    Returns:
        Series with divergence strength in [-100, 100]:
        - Positive: price up but volume weak
        - Negative: price down but volume weak
        - 0: price and volume move together
    """
    ret_short = df.get("return_1d", pd.Series(np.nan, index=df.index))
    vol_trend = volume_trend(df)

    # Price direction
    price_dir = ret_short.fillna(0).apply(lambda x: 1.0 if x > 0.005 else (-1.0 if x < -0.005 else 0.0))

    # When price moves but volume doesn't, flag it
    divergence = pd.Series(0.0, index=df.index, dtype=float)

    # Price up but volume weak
    up_weak_vol = (price_dir > 0) & (vol_trend < 0.5)
    divergence.loc[up_weak_vol] = 50.0

    # Price down but volume weak
    down_weak_vol = (price_dir < 0) & (vol_trend > -0.5)
    divergence.loc[down_weak_vol] = -50.0

    return divergence


def volume_confirmation_context(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all volume confirmation signals at once.

    Returns a DataFrame with columns:
    - vol_trend: volume direction trend
    - mom_vol_align: momentum aligned with volume
    - breakout_confirmed: range expansion confirmed by volume
    - price_vol_div: divergence magnitude
    """
    out = pd.DataFrame(index=df.index)
    out["vol_trend"] = volume_trend(df)
    out["mom_vol_align"] = momentum_volume_alignment(df)
    out["breakout_confirmed"] = breakout_volume_confirmation(df)
    out["price_vol_div"] = price_volume_divergence(df)
    return out
