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


def monte_carlo_full_display(
    prices: pd.Series,
    horizon: int = 20,
    simulations: int = 5000,
    seed: int = 42,
) -> dict[str, float]:
    """Monte Carlo display with full distribution information.

    Returns all key statistics from Monte Carlo simulation:
    - p_up: probability of positive return
    - p_down: probability of negative return
    - median_return: 50th percentile
    - expected_return: mean return
    - p10_return: 10th percentile
    - p90_return: 90th percentile
    - prob_range: natural language probability statement
    """
    returns = prices.pct_change().dropna().to_numpy()
    if len(returns) < 60:
        return {
            "p_up": np.nan,
            "p_down": np.nan,
            "median_return": np.nan,
            "expected_return": np.nan,
            "p10_return": np.nan,
            "p90_return": np.nan,
            "prob_range": "Dữ liệu không đủ",
        }

    rng = np.random.default_rng(seed)
    mu = np.mean(returns[-252:])
    sigma = np.std(returns[-252:], ddof=1)
    shocks = rng.normal(mu, sigma, size=(simulations, horizon))
    terminal = np.exp(np.log(prices.iloc[-1]) + shocks.sum(axis=1))
    terminal_return = terminal / prices.iloc[-1] - 1.0

    p_up = float(np.mean(terminal_return > 0))
    p_down = 1.0 - p_up
    median_ret = float(np.median(terminal_return))
    expected_ret = float(np.mean(terminal_return))
    p10_ret = float(np.percentile(terminal_return, 10))
    p90_ret = float(np.percentile(terminal_return, 90))

    # Natural language probability statement
    prob_pct = int(p_up * 100)
    if prob_pct >= 70:
        prob_range = f"Cao ({prob_pct}%): Xác suất tăng"
    elif prob_pct >= 60:
        prob_range = f"Tương đối ({prob_pct}%): Nhiều khả năng tăng"
    elif prob_pct > 50:
        prob_range = f"Hơi (+{prob_pct - 50}%): Hơi nghiêng về tăng"
    elif prob_pct == 50:
        prob_range = "Cân bằng (50%): Hai chiều ngang nhau"
    else:
        prob_range = f"Hơi ({100 - prob_pct}%): Hơi nghiêng về giảm"

    return {
        "p_up": p_up,
        "p_down": p_down,
        "median_return": median_ret,
        "expected_return": expected_ret,
        "p10_return": p10_ret,
        "p90_return": p90_ret,
        "prob_range": prob_range,
    }


def monte_carlo_score(
    df: pd.DataFrame,
    horizon: int = 20,
    simulations: int = 1000,
    lookback: int = 252,
    stride: int = 5,
    seed: int = 42,
) -> pd.Series:
    """Đưa kết quả Monte Carlo lên cùng thang [-100, 100] với các Score khác.

    Công thức mô phỏng không đổi: `monte_carlo_summary` được gọi trên cửa sổ giá
    quá khứ mỗi `stride` phiên, và xác suất tăng được ánh xạ tuyến tính thành
    ``100 * (2 * p_up - 1)``. Đây chỉ là phép đổi thang để so sánh, không phải một
    mô hình mới.
    """
    out = pd.Series(np.nan, index=df.index, dtype=float)

    for _, group in df.groupby("symbol", sort=False):
        ordered = group.sort_values("date")
        closes = ordered["close"]
        values = np.full(len(ordered), np.nan)
        current = np.nan

        for i in range(len(ordered)):
            if i >= 60 and (i - 60) % max(1, stride) == 0:
                window = closes.iloc[max(0, i - lookback + 1): i + 1]
                p_up = monte_carlo_summary(
                    window,
                    horizon=horizon,
                    simulations=simulations,
                    seed=seed,
                )["p_up"]
                current = np.nan if pd.isna(p_up) else 100.0 * (2.0 * float(p_up) - 1.0)
            values[i] = current

        out.loc[ordered.index] = values

    return out
