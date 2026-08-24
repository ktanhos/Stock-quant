from __future__ import annotations

import pandas as pd

from stock_quant.features import add_price_features
from stock_quant.models import (
    classify_regime,
    directional_edge,
    ewma_volatility,
    manipulation_guard_score,
    mean_reversion_score,
    persistence_features,
    persistence_score,
    range_expansion_score,
    risk_adjustment,
    tail_score,
    tsm_score,
    vol_adjusted_score,
    volatility_score,
    yang_zhang_volatility,
)
from stock_quant.research.targets import add_forward_returns


def run_signal_pipeline(price_df: pd.DataFrame) -> pd.DataFrame:
    """Run all deterministic signals for one or many symbols."""
    df = add_price_features(price_df)
    df = persistence_features(df)
    df["ewma_vol"] = ewma_volatility(df)
    df["yz_vol"] = yang_zhang_volatility(df)
    df["tsm_score"] = tsm_score(df)
    df["mr_score"] = mean_reversion_score(df)
    df["exp_score"] = range_expansion_score(df)
    df["vrh_score"] = persistence_score(df)
    df["vsf_score"] = volatility_score(df)
    df["vol_score"] = vol_adjusted_score(df)
    df["tail_score"] = tail_score(df)
    df["man_score"] = manipulation_guard_score(df)
    df["regime"] = classify_regime(df)
    df["directional_edge"] = directional_edge(df)
    df["risk_adjustment"] = risk_adjustment(df)
    df = add_forward_returns(df)
    return df


def latest_analysis(df: pd.DataFrame, symbols: list[str] | None = None) -> pd.DataFrame:
    out = df.copy()
    if symbols:
        wanted = {s.upper() for s in symbols}
        out = out[out["symbol"].str.upper().isin(wanted)]
    latest = out.sort_values("date").groupby("symbol", as_index=False).tail(1)
    columns = [
        "date",
        "symbol",
        "tsm_score",
        "vrh_score",
        "exp_score",
        "mr_score",
        "vsf_score",
        "vol_score",
        "tail_score",
        "man_score",
        "regime",
        "directional_edge",
        "risk_adjustment",
        "ewma_vol",
        "yz_vol",
        "future_return_5d",
        "future_return_20d",
        "future_return_60d",
    ]
    return latest[[c for c in columns if c in latest.columns]].sort_values("symbol").reset_index(drop=True)
