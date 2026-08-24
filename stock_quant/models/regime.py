from __future__ import annotations

import numpy as np
import pandas as pd


def classify_regime(df: pd.DataFrame) -> pd.Series:
    """Simple descriptive regime label; it does not create a trading signal."""
    out = pd.Series("unknown", index=df.index, dtype="object")
    trend = df["vrh_score"]
    stretch = df["mr_score"]
    expansion = df["exp_score"]

    out.loc[(trend > 25) & (expansion > 25)] = "trend_expansion"
    out.loc[(trend < -25) & (stretch.abs() < 35)] = "mean_reversion"
    out.loc[(expansion > 50) & (trend <= 25)] = "high_expansion_uncertain"
    out.loc[(trend.abs() <= 25) & (expansion.abs() <= 25)] = "range"
    return out


def directional_edge(df: pd.DataFrame) -> pd.Series:
    """Descriptive combined directional score; weights are intentionally explicit."""
    return (
        0.50 * df["tsm_score"]
        + 0.20 * df["vrh_score"]
        + 0.20 * df["exp_score"]
        + 0.10 * df["mr_score"]
    ).clip(-100, 100)


def risk_adjustment(df: pd.DataFrame) -> pd.Series:
    """Risk penalty is kept separate from directional edge."""
    tail = df["tail_score"].fillna(0.0)
    manipulation = df["man_score"].fillna(0.0)
    vol = df["vsf_score"].fillna(0.0).abs()
    return (100.0 - 0.35 * vol - 0.35 * np.maximum(0.0, -tail) - 0.30 * np.maximum(0.0, -manipulation)).clip(0, 100)
