from __future__ import annotations

from typing import Iterable

import pandas as pd

from .schema import normalize_symbols


class VnstockClient:
    """Adapter for Vnstock with optional API key authentication."""

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from vnstock import Vnstock, register_user  # type: ignore
        except ImportError as exc:
            raise ImportError("Install or upgrade vnstock before using VnstockClient") from exc

        api_key = (api_key or "").strip()
        if api_key:
            register_user(api_key=api_key)

        self._Vnstock = Vnstock

    def fetch_price_history(
        self,
        symbols: str | Iterable[str],
        start: str,
        end: str,
    ) -> pd.DataFrame:
        rows: list[pd.DataFrame] = []

        for symbol in normalize_symbols(symbols):
            stock = self._Vnstock().stock(symbol=symbol)
            history = stock.quote.history(start=start, end=end)

            if history is None or history.empty:
                continue

            frame = history.copy().rename(columns={"time": "date", "ticker": "symbol"})
            frame["symbol"] = symbol

            required = ["symbol", "date", "open", "high", "low", "close", "volume"]
            missing = [column for column in required if column not in frame.columns]
            if missing:
                raise ValueError(
                    f"Vnstock returned incomplete OHLCV data for {symbol}: {missing}"
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
                columns=["symbol", "date", "open", "high", "low", "close", "volume", "value"]
            )

        return (
            pd.concat(rows, ignore_index=True)
            .sort_values(["symbol", "date"])
            .reset_index(drop=True)
        )
