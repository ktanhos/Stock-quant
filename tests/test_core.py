import numpy as np
import pandas as pd

from stock_quant.data.schema import normalize_symbols, validate_price_frame
from stock_quant.features import add_price_features
from stock_quant.research.redundancy import correlation_matrix
from stock_quant.research.targets import add_forward_returns


def sample_prices() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=80, freq="B")
    rows = []
    for symbol, base in [("MSR", 100.0), ("FPT", 120.0)]:
        for i, date in enumerate(dates):
            close = base * (1 + 0.001 * i + 0.01 * np.sin(i / 5))
            rows.append(
                {
                    "symbol": symbol,
                    "date": date,
                    "open": close * 0.995,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1_000_000 + i * 1000,
                    "value": close * (1_000_000 + i * 1000),
                }
            )
    return pd.DataFrame(rows)


def test_normalize_symbols():
    assert normalize_symbols("msr, fpt") == ["FPT", "MSR"]


def test_validate_and_forward_returns():
    df = sample_prices()
    result = validate_price_frame(df)
    assert result.valid
    features = add_price_features(df)
    targets = add_forward_returns(features, horizons=(5, 20))
    assert "return_20d" in targets.columns
    assert "future_return_20d" in targets.columns


def test_redundancy_matrix():
    df = sample_prices()
    df["tsm_score"] = df["close"]
    df["exp_score"] = df["close"] * 0.5
    corr = correlation_matrix(df)
    assert corr.loc["tsm_score", "exp_score"] > 0.99
