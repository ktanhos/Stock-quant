from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from typing import Iterable

import pandas as pd

from .schema import normalize_symbols


class VnstockClient:
    """Adapter supporting Vnstock Community and Vnstock Data Unified UI."""

    def __init__(self, mode: str = "free", chunk_days: int = 90) -> None:
        if mode not in {"free", "registered"}:
            raise ValueError("Chế độ dữ liệu không hợp lệ")

        self.mode = mode
        self.chunk_days = max(30, int(chunk_days))
        self._market_class = self._load_market()

    def _load_market(self):
        if self.mode == "registered":
            try:
                from vnstock_data import Market  # type: ignore
                return Market
            except ImportError as exc:
                raise ImportError(
                    "Không tìm thấy vnstock_data trong môi trường Python đang chạy Streamlit."
                ) from exc

        try:
            from vnstock.ui import Market  # type: ignore
            return Market
        except ImportError:
            from vnstock import Market  # type: ignore
            return Market

    def _fetch_history(
        self,
        market,
        symbol: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        frames = []
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

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def _process_symbol(
        self,
        symbol: str,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
    ) -> pd.DataFrame | None:
        """Fetch và xử lý dữ liệu một symbol."""
        market = self._market_class()
        history = self._fetch_history(market, symbol, start_ts, end_ts)

        if history.empty:
            return None

        frame = history.rename(
            columns={"time": "date", "datetime": "date"}
        ).copy()
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
            column for column in required
            if column not in frame.columns
        ]
        if missing:
            raise ValueError(
                f"Vnstock trả về thiếu cột cho {symbol}: {missing}"
            )

        frame["date"] = pd.to_datetime(
            frame["date"],
            errors="coerce",
        ).dt.tz_localize(None)

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

        return frame[
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

    def fetch_price_history(
        self,
        symbols: str | Iterable[str],
        start: str,
        end: str,
        max_workers: int = 4,
    ) -> pd.DataFrame:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        if start_ts > end_ts:
            raise ValueError("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc")

        symbol_list = normalize_symbols(symbols)
        rows = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_symbol,
                    symbol,
                    start_ts,
                    end_ts,
                ): symbol
                for symbol in symbol_list
            }

            for future in as_completed(futures):
                try:
                    frame = future.result()
                    if frame is not None:
                        rows.append(frame)
                except Exception as exc:
                    symbol = futures[future]
                    raise RuntimeError(
                        f"Lỗi khi fetch dữ liệu {symbol}: {exc}"
                    ) from exc

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
