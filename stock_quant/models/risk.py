from __future__ import annotations

import numpy as np
import pandas as pd


def tail_score(df: pd.DataFrame, window: int = 60) -> pd.Series:
    def score(s: pd.Series) -> float:
        x = s.dropna()
        if len(x) < 30:
            return np.nan
        skew = x.skew()
        left = abs(x[x < x.quantile(0.10)].mean())
        right = abs(x[x > x.quantile(0.90)].mean())
        return float(np.tanh((right - left) / max(x.std(ddof=0), 1e-9)))

    return df.groupby("symbol")["return_1d"].transform(lambda s: s.rolling(window).apply(score, raw=False)) * 100.0


def manipulation_guard_score(df: pd.DataFrame) -> pd.Series:
    gap = df["gap_return"].abs()
    intraday = df["intraday_return"].abs()
    volume = df["relative_volume_20d"]
    abnormal = 0.5 * np.clip(gap / 0.05, 0, 2) + 0.5 * np.clip(intraday / 0.05, 0, 2)
    abnormal *= np.clip(volume / 2, 0.5, 2.0)
    return -100.0 * np.tanh(abnormal / 2.0)


def monte_carlo_summary(
    prices: pd.Series,
    horizon: int = 20,
    simulations: int = 5000,
    seed: int = 42,
) -> dict[str, float]:
    returns = prices.pct_change().dropna().to_numpy()
    if len(returns) < 60:
        return {"p_up": np.nan, "p50_return": np.nan, "expected_return": np.nan}
    rng = np.random.default_rng(seed)
    mu = np.mean(returns[-252:])
    sigma = np.std(returns[-252:], ddof=1)
    shocks = rng.normal(mu, sigma, size=(simulations, horizon))
    terminal = np.exp(np.log(prices.iloc[-1]) + shocks.sum(axis=1))
    terminal_return = terminal / prices.iloc[-1] - 1.0
    return {
        "p_up": float(np.mean(terminal_return > 0)),
        "p50_return": float(np.median(terminal_return)),
        "expected_return": float(np.mean(terminal_return)),
    }
