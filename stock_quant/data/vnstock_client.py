from __future__ import annotations

from typing import Iterable

import pandas as pd

from .schema import normalize_symbols


class VnstockClient:
    """Adapter for Vnstock 4 Unified UI."""

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from vnstock.ui import Market  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Vnstock 4 is required. Install or upgrade with: pip install -U vnstock"
            ) from exc

        self._Market = Market
        self._api_key = (api_key or "").strip()

    def fetch_price_history(
        self,
        symbols: str | Iterable[str],
        start: str,
        end: str,
    ) -> pd.DataFrame:
        rows: list[pd.DataFrame] = []
        market = self._Market()

        for symbol in normalize_symbols(symbols):
            history = market.equity(symbol).ohlcv(
                start=start,
                end=end,
                interval="1D",
            )

            if history is None or history.empty:
                continue

            frame = history.copy().rename(columns={"time": "date"})
            frame["symbol"] = symbol

            required = ["symbol", "date", "open", "high", "low", "close", "volume"]
            missing = [column for column in required if column not in frame.columns]
            if missing:
                raise ValueError(
                    f"Vnstock returned incomplete OHLCV data for {symbol}: {missing}"
                )

            frame["date"] = pd.to_datetime(frame["date"])
            for column in ["open", "high", "low", "close", "volume"]:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")

            frame = frame.dropna(
                subset=["date", "open", "high", "low", "close", "volume"]
            )

            if "value" not in frame.columns:
                frame["value"] = frame["close"] * frame["volume"]

            rows.append(
                frame[
                    ["symbol", "date", "open", "high", "low", "close", "volume", "value"]
                ]
            )

        if not rows:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "value",
                ]
            )

        return (
            pd.concat(rows, ignore_index=True)
            .sort_values(["symbol", "date"])
            .reset_index(drop=True)
        )
