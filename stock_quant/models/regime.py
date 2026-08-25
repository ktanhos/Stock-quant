from __future__ import annotations

import numpy as np
import pandas as pd

STOCK_REGIME_UPTREND = "xu_huong_tang"
STOCK_REGIME_EXPANSION = "mo_rong"
STOCK_REGIME_MEAN_REVERSION = "quay_ve_trung_binh"
STOCK_REGIME_DOWNTREND = "xu_huong_giam"
STOCK_REGIME_CONSOLIDATION = "con_soan"
STOCK_REGIME_UNKNOWN = "chua_du_du_lieu"

RISK_LOW = "THẤP"
RISK_MEDIUM = "TRUNG BÌNH"
RISK_HIGH = "CAO"
RISK_VERY_HIGH = "RẤT CAO"
RISK_UNKNOWN = "CHƯA XÁC ĐỊNH"

_REGIME_LABELS = {
    STOCK_REGIME_UPTREND: "Xu hướng tăng",
    STOCK_REGIME_EXPANSION: "Mở rộng",
    STOCK_REGIME_MEAN_REVERSION: "Quay về trung bình",
    STOCK_REGIME_DOWNTREND: "Xu hướng giảm",
    STOCK_REGIME_CONSOLIDATION: "Còn soan",
    STOCK_REGIME_UNKNOWN: "Chưa đủ dữ liệu",
}

_REGIME_DESCRIPTIONS = {
    STOCK_REGIME_UPTREND: "Giá đi lên với khí thế tích cực.",
    STOCK_REGIME_EXPANSION: "Biên độ mở rộng với khí thế đi lên.",
    STOCK_REGIME_MEAN_REVERSION: "Giá quay về trung bình sau biến động.",
    STOCK_REGIME_DOWNTREND: "Giá đi xuống với khí thế tiêu cực.",
    STOCK_REGIME_CONSOLIDATION: "Giá đi ngang trong biên độ hẹp.",
    STOCK_REGIME_UNKNOWN: "Không đủ dữ liệu để phân tích.",
}

_REGIME_RISK = {
    STOCK_REGIME_UPTREND: RISK_LOW,
    STOCK_REGIME_EXPANSION: RISK_MEDIUM,
    STOCK_REGIME_MEAN_REVERSION: RISK_MEDIUM,
    STOCK_REGIME_DOWNTREND: RISK_HIGH,
    STOCK_REGIME_CONSOLIDATION: RISK_LOW,
    STOCK_REGIME_UNKNOWN: RISK_UNKNOWN,
}


def classify_regime(df: pd.DataFrame) -> pd.Series:
    """Enhanced stock-level regime classification based on multiple score indicators.

    Uses 5 scores to classify into 6 regimes:
    - Trend (vrh_score): persistence of price movement
    - Momentum (tsm_score): price acceleration
    - Mean Reversion (mr_score): deviation from average
    - Expansion (exp_score): volatility increase
    - Volatility (vsf_score): market uncertainty
    """
    out = pd.Series(STOCK_REGIME_UNKNOWN, index=df.index, dtype="object")

    trend = df.get("vrh_score", pd.Series(0.0, index=df.index)).fillna(0.0)
    momentum = df.get("tsm_score", pd.Series(0.0, index=df.index)).fillna(0.0)
    stretch = df.get("mr_score", pd.Series(0.0, index=df.index)).fillna(0.0)
    expansion = df.get("exp_score", pd.Series(0.0, index=df.index)).fillna(0.0)
    volatility = df.get("vsf_score", pd.Series(0.0, index=df.index)).fillna(0.0).abs()

    # Uptrend: strong positive trend + positive momentum, low volatility
    uptrend_mask = (trend > 30) & (momentum > 20) & (volatility < 50)
    out.loc[uptrend_mask] = STOCK_REGIME_UPTREND

    # Expansion: increasing volatility with positive direction
    expansion_mask = (expansion > 40) & (momentum > 10) & ~uptrend_mask
    out.loc[expansion_mask] = STOCK_REGIME_EXPANSION

    # Mean Reversion: price deviated significantly and momentum contradicts direction
    mean_rev_mask = (
        (stretch.abs() > 40) &
        ((momentum * stretch) < 0) &  # opposite signs
        ~uptrend_mask &
        ~expansion_mask
    )
    out.loc[mean_rev_mask] = STOCK_REGIME_MEAN_REVERSION

    # Downtrend: negative trend + negative momentum
    downtrend_mask = (trend < -30) & (momentum < -20) & ~mean_rev_mask
    out.loc[downtrend_mask] = STOCK_REGIME_DOWNTREND

    # Consolidation: all indicators near neutral, low volatility
    consolidation_mask = (
        (trend.abs() < 20) &
        (momentum.abs() < 20) &
        (expansion.abs() < 30) &
        (volatility < 30) &
        ~uptrend_mask &
        ~expansion_mask &
        ~mean_rev_mask &
        ~downtrend_mask
    )
    out.loc[consolidation_mask] = STOCK_REGIME_CONSOLIDATION

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


def regime_risk(regime: pd.Series) -> pd.Series:
    """Risk level based on regime."""
    return regime.map(lambda r: _REGIME_RISK.get(r, RISK_UNKNOWN))


def regime_interpretation(df: pd.DataFrame) -> pd.DataFrame:
    """Provide regime context: label, confidence, risk, and description.

    Returns a DataFrame with columns:
    - regime_label: descriptive regime name (Vietnamese)
    - regime_strength: confidence in regime classification [0, 100]
    - regime_description: brief character description
    - regime_risk: estimated risk level
    """
    out = pd.DataFrame(index=df.index)
    regime = classify_regime(df)
    out["regime_key"] = regime
    out["regime_label"] = regime.map(lambda r: _REGIME_LABELS.get(r, "Chưa xác định"))
    out["regime_description"] = regime.map(lambda r: _REGIME_DESCRIPTIONS.get(r, ""))
    out["regime_risk"] = regime_risk(regime)

    # Calculate regime strength (confidence) based on how clearly scores confirm regime
    trend = df.get("vrh_score", pd.Series(0.0, index=df.index)).fillna(0.0).abs()
    momentum = df.get("tsm_score", pd.Series(0.0, index=df.index)).fillna(0.0).abs()
    stretch = df.get("mr_score", pd.Series(0.0, index=df.index)).fillna(0.0).abs()
    expansion = df.get("exp_score", pd.Series(0.0, index=df.index)).fillna(0.0).abs()

    # Normalize to [0, 1] scale
    normalized_trend = (trend / 100.0).clip(0, 1.0)
    normalized_momentum = (momentum / 100.0).clip(0, 1.0)
    normalized_stretch = (stretch / 100.0).clip(0, 1.0)
    normalized_expansion = (expansion / 100.0).clip(0, 1.0)

    # Average of absolute score strengths = how confident are we in the regime
    out["regime_strength"] = 100.0 * (
        normalized_trend + normalized_momentum + normalized_stretch + normalized_expansion
    ) / 4.0

    return out
