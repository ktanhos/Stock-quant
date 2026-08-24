from __future__ import annotations

import os
from datetime import timedelta
from typing import Iterable

import pandas as pd

from .schema import normalize_symbols


class VnstockClient:
    """Unified adapter for Vnstock Community and Vnstock Data."""

    def __init__(
        self,
        mode: str = "free",
        api_key: str | None = None,
        chunk_days: int = 90,
    ) -> None:
        if mode not in {"free", "registered"}:
            raise ValueError("mode must be 'free' or 'registered'")

        self.mode = mode
        self.api_key = (api_key or "").strip()
        self.chunk_days = max(30, int(chunk_days))
        self._Market = self._load_market()

    def _load_market(self):
        if self.mode == "registered":
            if not self.api_key:
                raise ValueError("Chế độ API đã đăng ký yêu cầu nhập API Key")

            # Gói vnstock_data nhận diện thông tin tài khoản/API Key của gói tài trợ.
            os.environ["VNSTOCK_API_KEY"] = self.api_key

            try:
                from vnstock_data import Market  # type: ignore
                return Market
            except ImportError as exc:
                raise ImportError(
                    "Không tìm thấy vnstock_data. Cần cài gói dữ liệu đã đăng ký "
                    "theo trình cài đặt chính thức của Vnstock."
                ) from exc

        try:
            from vnstock.ui import Market  # type: ignore
        except ImportError:
            try:
                from vnstock import Market  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "Không tìm thấy vnstock. Chạy: pip install -U vnstock"
                ) from exc

        if self.api_key:
            # API Key của bản Community giúp xác thực/hạn mức khi thư viện hỗ trợ.
            try:
                from vnstock import register_user  # type: ignore
                register_user(api_key=self.api_key)
            except Exception:
                # Không làm hỏng chế độ miễn phí nếu phiên bản thư viện không có hàm này.
                pass

        return Market

    def _fetch_chunked(self, market, symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        current = start

        while current <= end:
            chunk_end = min(current + timedelta(days=self.chunk_days - 1), end)

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

        rows: list[pd.DataFrame] = []
        market = self._Market()

        for symbol in normalize_symbols(symbols):
            history = self._fetch_chunked(market, symbol, start_ts, end_ts)

            if history.empty:
                continue

            frame = history.rename(columns={"time": "date"}).copy()
            frame["symbol"] = symbol

            required = ["symbol", "date", "open", "high", "low", "close", "volume"]
            missing = [column for column in required if column not in frame.columns]
            if missing:
                raise ValueError(
                    f"Vnstock trả về thiếu cột cho {symbol}: {missing}"
                )

            frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None)
            for column in ["open", "high", "low", "close", "volume"]:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")

            frame = frame.dropna(
                subset=["date", "open", "high", "low", "close", "volume"]
            )
            frame = frame[
                (frame["date"] >= start_ts) & (frame["date"] <= end_ts)
            ]

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
                    "symbol", "date", "open", "high", "low",
                    "close", "volume", "value",
                ]
            )

        return (
            pd.concat(rows, ignore_index=True)
            .drop_duplicates(subset=["symbol", "date"], keep="last")
            .sort_values(["symbol", "date"])
            .reset_index(drop=True)
        )
