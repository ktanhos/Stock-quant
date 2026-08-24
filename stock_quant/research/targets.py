from __future__ import annotations

import pandas as pd


def add_forward_returns(df: pd.DataFrame, horizons: tuple[int, ...] = (5, 10, 20, 60)) -> pd.DataFrame:
    out = df.copy()
    grouped = out.groupby("symbol")["close"]
    for horizon in horizons:
        future = grouped.shift(-horizon)
        out[f"future_return_{horizon}d"] = future / out["close"] - 1.0
    return out
