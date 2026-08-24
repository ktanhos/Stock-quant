import numpy as np
import pandas as pd

from stock_quant.analysis import latest_analysis, run_signal_pipeline


def make_prices(symbols=("MSR", "FPT"), periods=140):
    dates = pd.date_range("2024-01-01", periods=periods, freq="B")
    rows = []
    for j, symbol in enumerate(symbols):
        base = 100 + 20 * j
        for i, date in enumerate(dates):
            close = base * np.exp(0.001 * i + 0.015 * np.sin(i / 7))
            rows.append({
                "symbol": symbol,
                "date": date,
                "open": close * 0.998,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 1_000_000 + i * 2_000,
                "value": close * (1_000_000 + i * 2_000),
            })
    return pd.DataFrame(rows)


def test_pipeline_supports_multiple_symbols():
    result = run_signal_pipeline(make_prices())
    assert set(result["symbol"]) == {"MSR", "FPT"}
    assert {"directional_edge", "risk_adjustment", "regime"}.issubset(result.columns)

    latest = latest_analysis(result)
    assert set(latest["symbol"]) == {"MSR", "FPT"}
