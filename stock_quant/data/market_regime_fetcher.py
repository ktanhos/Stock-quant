"""Fetch VNINDEX data and calculate market regime."""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta

from stock_quant.models.market_context import build_market_regime
from stock_quant.data.vnstock_client import VnstockClient


def fetch_vnindex_data(
    end_date: datetime | None = None,
    lookback_days: int = 400,
) -> pd.DataFrame | None:
    """Fetch VNINDEX OHLC data for market regime calculation.

    Args:
        end_date: End date for the fetch (defaults to today)
        lookback_days: Number of business days to fetch (default 400)

    Returns:
        DataFrame with OHLC data, or None if fetch fails
    """
    if end_date is None:
        end_date = datetime.now()

    start_date = end_date - timedelta(days=int(lookback_days * 1.4))

    try:
        client = VnstockClient()
        data = client.fetch_index(
            symbol="VNINDEX",
            start=start_date.date(),
            end=end_date.date(),
        )
        if data is None or data.empty:
            return None
        return data.sort_values("date").reset_index(drop=True)
    except Exception:
        return None


def calculate_market_regime(
    vnindex_df: pd.DataFrame | None = None,
    end_date: datetime | None = None,
) -> dict:
    """Calculate market regime from VNINDEX data.

    Args:
        vnindex_df: Pre-fetched VNINDEX data (if None, fetches automatically)
        end_date: Reference date for regime calculation

    Returns:
        dict with regime, risk_level, trend, stress info, or empty dict if calculation fails
    """
    if vnindex_df is None or vnindex_df.empty:
        vnindex_df = fetch_vnindex_data(end_date=end_date)

    if vnindex_df is None or vnindex_df.empty:
        return {
            "regime": "CHƯA ĐỦ DỮ LIỆU",
            "risk_level": "CHƯA XÁC ĐỊNH",
            "regime_description": "Không thể tính toán trạng thái thị trường do thiếu dữ liệu.",
            "trend": {"state": "CHƯA ĐỦ DỮ LIỆU"},
            "stress": {"state": "CHƯA ĐỦ DỮ LIỆU"},
        }

    try:
        close = vnindex_df["close"]
        high = vnindex_df["high"]
        low = vnindex_df["low"]

        regime = build_market_regime(close, high, low)
        return regime
    except Exception:
        return {
            "regime": "CHƯA ĐỦ DỮ LIỆU",
            "risk_level": "CHƯA XÁC ĐỊNH",
            "regime_description": "Lỗi khi tính toán trạng thái thị trường.",
            "trend": {"state": "CHƯA ĐỦ DỮ LIỆU"},
            "stress": {"state": "CHƯA ĐỦ DỮ LIỆU"},
        }
