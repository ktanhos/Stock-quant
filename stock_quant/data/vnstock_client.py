from __future__ import annotations

import importlib.util
from datetime import timedelta
from typing import Iterable

import pandas as pd

from .schema import normalize_symbols


class VnstockClient:
    """Adapter for Vnstock Community and Vnstock Data."""

    def __init__(self, mode: str = "free", chunk_days: int = 90) -> None:
        if mode not in {"free", "registered"}:
            raise ValueError("mode must be 'free' or 'registered'")

        self.mode = mode
        self.chunk_days = max(30, int(chunk_days))
        self._Market = self._load_market()

    @staticmethod
    def registered_package_available() -> bool:
        return importlib.util.find_spec("vnstock_data") is not None

    def _load_market(self):
        if self.mode == "registered":
            try:
                from vnstock_data import Market  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "Môi trường hiện tại chưa có thư viện vnstock_data. "
                    "API Key hợp lệ không thể tự cài thư viện này."
                ) from exc
            return Market

        try:
            from vnstock.ui import Market  # type: ignore
            return Market
        except ImportError:
            try:
                from vnstock import Market  # type: ignore
                return Market
            except ImportError as exc:
                raise ImportError(
                    "Không tìm thấy thư viện vnstock. Chạy: pip install -U vnstock"
                ) from exc

    def _fetch_chunked(
        self,
        market,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        current = start

        while current <= end:
            chunk_end = min(
                current + timedelta(days=self.chunk_days - 1),
                end,
            )

            history = market.equity(symbol).ohlcv(
                start=current.strftime("%Y-%m-%d"),
                end=chunk_end.strftime("%Y-%m-%d"),
                interval="1D",
            )

            if history is not None and not history.empty:
                frames.append(history.copy())

            current = chunk_end + timedelta(days=1)

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)

    def fetch_price_history(
        self,
        symbols: str | Iterable[str],
        start: str,
        end: str,
    ) -> pd.DataFrame:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        if start_ts > end_ts:
            raise ValueError("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc")

        market = self._Market()
        rows: list[pd.DataFrame] = []

        for symbol in normalize_symbols(symbols):
            history = self._fetch_chunked(
                market,
                symbol,
                start_ts,
                end_ts,
            )

            if history.empty:
                continue

            frame = history.rename(columns={"time": "date"}).copy()
            frame["symbol"] = symbol

            required = [
                "symbol",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
            missing = [
                column for column in required if column not in frame.columns
            ]
            if missing:
                raise ValueError(
                    f"Vnstock trả về thiếu cột cho {symbol}: {missing}"
                )

            frame["date"] = (
                pd.to_datetime(frame["date"], errors="coerce")
                .dt.tz_localize(None)
            )

            for column in ["open", "high", "low", "close", "volume"]:
                frame[column] = pd.to_numeric(
                    frame[column],
                    errors="coerce",
                )

            frame = frame.dropna(subset=required[1:])
            frame = frame[
                (frame["date"] >= start_ts)
                & (frame["date"] <= end_ts)
            ]

            if "value" not in frame.columns:
                frame["value"] = frame["close"] * frame["volume"]

            rows.append(
                frame[
                    [
                        "symbol",
                        "date",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "value",
                    ]
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
            .drop_duplicates(subset=["symbol", "date"], keep="last")
            .sort_values(["symbol", "date"])
            .reset_index(drop=True)
        )
