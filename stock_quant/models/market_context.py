"""Market regime classification for VNINDEX.

Calculates five market state indicators:
* Trend (RORO): momentum relative to 49-period baseline
* Stress: volatility vs historical levels
* Breadth: VN30 participation (optional, if data available)
* Dispersion: return variation within VN30 (optional)
* Concentration: risk concentration (optional)

Returns market regime and risk level without creating trading signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REGIME_FAVOURABLE = "THUẬN LỢI"
REGIME_WARNING = "CẢNH BÁO"
REGIME_TRANSITION = "CHUYỂN TIẾP"
REGIME_UNDER_PRESSURE = "CHỊU ÁP LỰC"
REGIME_STRESSED = "CĂNG THẲNG"
REGIME_UNKNOWN = "CHƯA ĐỦ DỮ LIỆU"

RISK_LOW = "THẤP"
RISK_MEDIUM = "TRUNG BÌNH"
RISK_HIGH = "CAO"
RISK_VERY_HIGH = "RẤT CAO"
RISK_UNKNOWN = "CHƯA XÁC ĐỊNH"

TREND_POSITIVE = "TÍCH CỰC"
TREND_NEUTRAL = "TRUNG TÍNH"
TREND_WEAK = "SUY YẾU"
TREND_UNKNOWN = "CHƯA ĐỦ DỮ LIỆU"

STRESS_LOW = "THẤP"
STRESS_NORMAL = "BÌNH THƯỜNG"
STRESS_HIGH = "CAO"
STRESS_VERY_HIGH = "RẤT CAO"
STRESS_UNKNOWN = "CHƯA ĐỦ DỮ LIỆU"

_DESCRIPTIONS = {
    REGIME_FAVOURABLE: (
        "Xu hướng VNINDEX tích cực, mức biến động bình thường "
        "và nhóm vốn hóa lớn đang đồng thuận."
    ),
    REGIME_WARNING: (
        "Thị trường vẫn tăng nhưng rủi ro đã cao hơn: "
        "biến động tăng lên hoặc độ lan tỏa của nhóm VN30 đang mỏng dần."
    ),
    REGIME_TRANSITION: (
        "Xu hướng đang thay đổi nhưng mức biến động chưa xác nhận. "
        "Nhóm cổ phiếu lớn chưa tạo ra sự đồng thuận rõ ràng."
    ),
    REGIME_UNDER_PRESSURE: (
        "Xu hướng suy yếu đi cùng biến động tăng."
    ),
    REGIME_STRESSED: (
        "Xu hướng suy yếu và mức biến động đang ở vùng cao nhất so với chính "
        "thị trường này trong một năm qua."
    ),
    REGIME_UNKNOWN: "Chưa đủ dữ liệu để mô tả trạng thái thị trường.",
}

_BASE_RISK = {
    REGIME_FAVOURABLE: RISK_LOW,
    REGIME_WARNING: RISK_MEDIUM,
    REGIME_TRANSITION: RISK_MEDIUM,
    REGIME_UNDER_PRESSURE: RISK_HIGH,
    REGIME_STRESSED: RISK_VERY_HIGH,
    REGIME_UNKNOWN: RISK_UNKNOWN,
}

_RISK_LADDER = [RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_VERY_HIGH]

RORO_HORIZONS = [(63, 0.4), (126, 0.2), (189, 0.2), (252, 0.2)]
RORO_BASELINE_WINDOW = 49
RORO_SIGMA_WINDOW = 252
RORO_NEUTRAL_SIGMA = 1.0


def calculate_strength(close: pd.Series) -> pd.Series:
    """Multi-timeframe momentum: weighted sum of ROC across 4 horizons."""
    close = pd.to_numeric(close, errors="coerce")
    total = None
    for horizon, weight in RORO_HORIZONS:
        part = close.pct_change(horizon) * weight
        total = part if total is None else total + part
    return (total * 100).rename("strength")


def calculate_trend(close: pd.Series) -> dict:
    """Calculate trend (RORO) and classify into POSITIVE/NEUTRAL/WEAK."""
    if len(close) < 300:
        return {
            "state": TREND_UNKNOWN,
            "roro": np.nan,
            "roro_band": np.nan,
            "strength": np.nan,
        }

    strength = calculate_strength(close)
    baseline = strength.rolling(RORO_BASELINE_WINDOW, min_periods=RORO_BASELINE_WINDOW).mean()
    roro = strength - baseline

    band = (
        roro.rolling(RORO_SIGMA_WINDOW, min_periods=60).std()
        * RORO_NEUTRAL_SIGMA
    )

    last_roro = float(roro.iloc[-1]) if pd.notna(roro.iloc[-1]) else np.nan
    last_band = float(band.iloc[-1]) if pd.notna(band.iloc[-1]) else np.nan

    if pd.isna(last_roro):
        state = TREND_UNKNOWN
    elif last_roro > last_band:
        state = TREND_POSITIVE
    elif last_roro < -last_band:
        state = TREND_WEAK
    else:
        state = TREND_NEUTRAL

    return {
        "state": state,
        "roro": last_roro,
        "roro_band": last_band,
        "strength": float(strength.iloc[-1]) if pd.notna(strength.iloc[-1]) else np.nan,
    }


def calculate_stress(close: pd.Series, high: pd.Series, low: pd.Series) -> dict:
    """Calculate volatility stress using Parkinson estimator."""
    if len(close) < 60:
        return {
            "state": STRESS_UNKNOWN,
            "volatility": np.nan,
            "volatility_historical_percentile": np.nan,
        }

    close = pd.to_numeric(close, errors="coerce")
    high = pd.to_numeric(high, errors="coerce")
    low = pd.to_numeric(low, errors="coerce")

    hl_ratio = np.log(high / low)
    parkinson_vol = np.sqrt(hl_ratio ** 2 / (4 * np.log(2)))

    vol_20d = parkinson_vol.rolling(20, min_periods=20).mean().iloc[-1]
    vol_252d = parkinson_vol.rolling(252, min_periods=252).std()

    if pd.isna(vol_20d) or pd.isna(vol_252d.iloc[-1]) or vol_252d.iloc[-1] <= 0:
        percentile = np.nan
    else:
        percentile = (
            (vol_20d - vol_252d.mean()) / vol_252d.iloc[-1] * 100
        ).clip(0, 100)

    if pd.isna(percentile):
        state = STRESS_UNKNOWN
    elif percentile > 75:
        state = STRESS_VERY_HIGH
    elif percentile > 50:
        state = STRESS_HIGH
    elif percentile > 25:
        state = STRESS_NORMAL
    else:
        state = STRESS_LOW

    return {
        "state": state,
        "volatility": float(vol_20d) if pd.notna(vol_20d) else np.nan,
        "volatility_historical_percentile": float(percentile) if pd.notna(percentile) else np.nan,
    }


def classify_regime(
    trend_state: str,
    stress_state: str,
) -> str:
    """Regime classification based on trend and stress states."""
    if trend_state in (None, TREND_UNKNOWN) or stress_state in (None, STRESS_UNKNOWN):
        return REGIME_UNKNOWN

    high_stress = stress_state in (STRESS_HIGH, STRESS_VERY_HIGH)
    extreme_stress = stress_state == STRESS_VERY_HIGH
    calm = stress_state in (STRESS_LOW, STRESS_NORMAL)

    if trend_state == TREND_WEAK and extreme_stress:
        return REGIME_STRESSED
    if trend_state == TREND_WEAK and high_stress:
        return REGIME_UNDER_PRESSURE
    if trend_state == TREND_POSITIVE and calm:
        return REGIME_FAVOURABLE
    if trend_state == TREND_POSITIVE and high_stress:
        return REGIME_WARNING
    if trend_state == TREND_NEUTRAL and extreme_stress:
        return REGIME_UNDER_PRESSURE
    return REGIME_TRANSITION


def risk_level(regime: str) -> tuple[str, str]:
    """Risk level and descriptive reason."""
    level = _BASE_RISK.get(regime, RISK_UNKNOWN)
    description = _DESCRIPTIONS.get(regime, _DESCRIPTIONS[REGIME_UNKNOWN])
    return level, description


def build_market_regime(close: pd.Series, high: pd.Series, low: pd.Series) -> dict:
    """Complete market regime analysis for VNINDEX."""
    trend = calculate_trend(close)
    stress = calculate_stress(close, high, low)

    regime = classify_regime(trend["state"], stress["state"])
    risk_l, risk_desc = risk_level(regime)

    return {
        "regime": regime,
        "regime_description": _DESCRIPTIONS.get(regime, _DESCRIPTIONS[REGIME_UNKNOWN]),
        "risk_level": risk_l,
        "risk_description": risk_desc,
        "trend": trend,
        "stress": stress,
    }
