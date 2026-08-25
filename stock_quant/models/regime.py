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


def regime_interpretation(df: pd.DataFrame) -> pd.DataFrame:
    """Provide regime context: label, confidence, and character description.

    Returns a DataFrame with columns:
    - regime_label: descriptive regime name
    - regime_strength: confidence in regime classification [0, 100]
    - regime_description: brief character description
    """
    out = pd.DataFrame(index=df.index)
    regime = classify_regime(df)
    out["regime_label"] = regime

    # Calculate regime strength based on signal spread
    trend = df.get("vrh_score", pd.Series(0.0, index=df.index)).fillna(0.0)
    stretch = df.get("mr_score", pd.Series(0.0, index=df.index)).fillna(0.0)
    expansion = df.get("exp_score", pd.Series(0.0, index=df.index)).fillna(0.0)

    # Strength: how clearly do scores confirm the regime?
    trend_strength = (trend.abs() / 100.0).clip(0, 1.0)
    expansion_strength = (expansion.abs() / 100.0).clip(0, 1.0)
    stretch_strength = (stretch.abs() / 100.0).clip(0, 1.0)

    out["regime_strength"] = 100.0 * (trend_strength + expansion_strength + stretch_strength) / 3.0

    # Regime character description
    out["regime_description"] = "Trung tính"
    out.loc[regime == "trend_expansion", "regime_description"] = "Xu hướng mở rộng"
    out.loc[regime == "mean_reversion", "regime_description"] = "Quay về trung bình"
    out.loc[regime == "high_expansion_uncertain", "regime_description"] = "Mở rộng cao nhưng không rõ"
    out.loc[regime == "range", "regime_description"] = "Đi trong biên độ"

    return out
