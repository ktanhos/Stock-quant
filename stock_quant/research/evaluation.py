from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def information_coefficient(signal: pd.Series, future_return: pd.Series) -> float:
    mask = signal.notna() & future_return.notna()
    if mask.sum() < 20:
        return np.nan
    return float(spearmanr(signal[mask], future_return[mask]).statistic)


def cross_sectional_ic(df: pd.DataFrame, signal_col: str, target_col: str) -> pd.DataFrame:
    rows = []
    for date, group in df.groupby("date"):
        ic = information_coefficient(group[signal_col], group[target_col])
        rows.append({"date": date, "ic": ic})
    return pd.DataFrame(rows)


def hit_ratio(signal: pd.Series, future_return: pd.Series) -> float:
    mask = signal.notna() & future_return.notna() & (signal != 0)
    if mask.sum() == 0:
        return np.nan
    return float((np.sign(signal[mask]) == np.sign(future_return[mask])).mean())


def predictive_summary(df: pd.DataFrame, signal_col: str, target_col: str) -> dict[str, float]:
    ic_series = cross_sectional_ic(df, signal_col, target_col)["ic"].dropna()
    return {
        "mean_ic": float(ic_series.mean()) if not ic_series.empty else np.nan,
        "ic_std": float(ic_series.std(ddof=1)) if len(ic_series) > 1 else np.nan,
        "ic_ir": float(ic_series.mean() / ic_series.std(ddof=1) * np.sqrt(252)) if len(ic_series) > 1 and ic_series.std(ddof=1) > 0 else np.nan,
        "hit_ratio": hit_ratio(df[signal_col], df[target_col]),
        "observations": float(df[[signal_col, target_col]].dropna().shape[0]),
    }
