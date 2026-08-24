from __future__ import annotations

from typing import Iterable

import pandas as pd

from .schema import normalize_symbols


class VnstockClient:
    """Thin adapter around vnstock. Import is deferred so core tests work without the package."""

    def __init__(self) -> None:
        try:
            from vnstock import Vnstock  # type: ignore
        except ImportError as exc:
            raise ImportError("Install vnstock before using VnstockClient") from exc
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
            frame = history.copy()
            rename = {
                "time": "date",
                "date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "value": "value",
            }
            frame = frame.rename(columns={k: v for k, v in rename.items() if k in frame.columns})
            frame["symbol"] = symbol
            if "value" not in frame.columns:
                frame["value"] = frame["close"] * frame["volume"]
            rows.append(frame[["symbol", "date", "open", "high", "low", "close", "volume", "value"]])

        if not rows:
            return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "value"])
        return pd.concat(rows, ignore_index=True).sort_values(["symbol", "date"]).reset_index(drop=True)
