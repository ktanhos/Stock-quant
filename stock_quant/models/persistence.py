from __future__ import annotations

import numpy as np
import pandas as pd


def _autocorr(series: pd.Series, lag: int = 1) -> float:
    return series.autocorr(lag=lag)


def _hurst_proxy(series: pd.Series) -> float:
    x = series.dropna().to_numpy()
    if len(x) < 40:
        return np.nan
    scales = np.array([2, 4, 8, 16], dtype=int)
    values = []
    valid_scales = []
    for scale in scales:
        n = len(x) // scale
        if n < 5:
            continue
        blocks = x[: n * scale].reshape(n, scale).sum(axis=1)
        variance = np.var(blocks, ddof=1)
        if variance > 0:
            values.append(variance)
            valid_scales.append(scale)
    if len(values) < 2:
        return np.nan
    slope = np.polyfit(np.log(valid_scales), np.log(values), 1)[0]
    return float(np.clip(slope / 2.0, 0.0, 1.0))


def persistence_features(df: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    pieces = []
    for symbol, group in df.groupby("symbol", sort=False):
        g = group.sort_values("date").copy()
        ret = g["return_1d"]
        g["ac1_60"] = ret.rolling(window).apply(lambda s: _autocorr(s, 1), raw=False)
        g["hurst_60"] = ret.rolling(window).apply(_hurst_proxy, raw=False)
        pieces.append(g)
    return pd.concat(pieces).sort_index()


def persistence_score(df: pd.DataFrame) -> pd.Series:
    ac = df.get("ac1_60", pd.Series(np.nan, index=df.index))
    h = df.get("hurst_60", pd.Series(np.nan, index=df.index))
    score = 0.55 * np.tanh(ac / 0.15) + 0.45 * np.tanh((h - 0.5) / 0.05)
    return 100.0 * score
