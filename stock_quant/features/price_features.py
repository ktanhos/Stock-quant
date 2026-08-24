from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window).mean()
    std = series.rolling(window).std(ddof=0)
    return (series - mean) / std.replace(0, np.nan)


def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["symbol", "date"]).reset_index(drop=True)
    grouped = out.groupby("symbol", group_keys=False)

    out["return_1d"] = grouped["close"].pct_change()
    for window in (5, 20, 60):
        out[f"return_{window}d"] = grouped["close"].pct_change(window)
        out[f"range_{window}d"] = (
            (out["high"] - out["low"]).div(out["close"].replace(0, np.nan))
            .groupby(out["symbol"])
            .rolling(window)
            .mean()
            .reset_index(level=0, drop=True)
        )
        out[f"close_z_{window}d"] = grouped["close"].transform(
            lambda s: _rolling_zscore(s, window)
        )
        out[f"volume_mean_{window}d"] = grouped["volume"].transform(
            lambda s: s.rolling(window).mean()
        )

    out["relative_volume_20d"] = out["volume"] / out["volume_mean_20d"].replace(0, np.nan)
    out["gap_return"] = out["open"] / grouped["close"].shift(1) - 1.0
    out["intraday_return"] = out["close"] / out["open"].replace(0, np.nan) - 1.0
    out["true_range"] = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - grouped["close"].shift(1)).abs(),
            (out["low"] - grouped["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr_20"] = out.groupby("symbol")["true_range"].transform(
        lambda s: s.rolling(20).mean()
    )
    out["atr_pct_20"] = out["atr_20"] / out["close"].replace(0, np.nan)

    return out
