from __future__ import annotations

import numpy as np
import pandas as pd


def ewma_volatility(df: pd.DataFrame, span: int = 20) -> pd.Series:
    return df.groupby("symbol")["return_1d"].transform(lambda s: s.ewm(span=span, adjust=False).std()) * np.sqrt(252.0)


def yang_zhang_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    prev_close = df.groupby("symbol")["close"].shift(1)
    open_price = df["open"].replace(0, np.nan)
    close_price = df["close"].replace(0, np.nan)
    overnight = np.log(open_price / prev_close.replace(0, np.nan))
    close_open = np.log(close_price / open_price)
    rs = np.log(df["high"] / close_price) * np.log(df["high"] / open_price) + np.log(
        df["low"] / close_price
    ) * np.log(df["low"] / open_price)
    out = []
    for _, g in pd.DataFrame({"overnight": overnight, "close_open": close_open, "rs": rs, "symbol": df["symbol"]}).groupby("symbol"):
        n = window
        sigma_o = g["overnight"].rolling(n).var()
        sigma_c = g["close_open"].rolling(n).var()
        sigma_rs = g["rs"].rolling(n).mean()
        k = 0.34 / (1.34 + (n + 1) / (n - 1))
        yz = sigma_o + k * sigma_c + (1 - k) * sigma_rs
        out.append(yz)
    return pd.concat(out).reindex(df.index).pow(0.5) * np.sqrt(252.0)


def volatility_score(df: pd.DataFrame) -> pd.Series:
    vol = df["ewma_vol"].replace(0, np.nan)
    relative = vol / vol.groupby(df["symbol"]).transform(lambda s: s.rolling(60).mean())
    return 100.0 * np.tanh((relative - 1.0) / 0.25)


def vol_adjusted_score(df: pd.DataFrame) -> pd.Series:
    momentum = df["return_20d"]
    vol = df["ewma_vol"].replace(0, np.nan)
    raw = momentum / (vol / np.sqrt(252.0))
    return 100.0 * np.tanh(raw / 2.0)
