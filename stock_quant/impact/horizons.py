"""Các horizon Future Return dùng cho tầng Score Impact."""

from __future__ import annotations

import pandas as pd

from stock_quant.research.targets import add_forward_returns

IMPACT_HORIZONS: tuple[int, ...] = (5, 20, 60)

HORIZON_LABELS = {5: "5D", 20: "20D", 60: "60D"}


def forward_return_column(horizon: int) -> str:
    return f"future_return_{horizon}d"


def horizon_label(horizon: int) -> str:
    return HORIZON_LABELS.get(horizon, f"{horizon}D")


def ensure_forward_returns(
    df: pd.DataFrame, horizons: tuple[int, ...] = IMPACT_HORIZONS
) -> pd.DataFrame:
    """Bổ sung các cột Future Return còn thiếu, giữ nguyên mọi cột đang có."""
    missing = tuple(h for h in horizons if forward_return_column(h) not in df.columns)
    if not missing:
        return df
    return add_forward_returns(df, horizons=missing)
