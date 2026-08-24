from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


PRICE_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "value"]


@dataclass(frozen=True)
class DataValidationResult:
    valid: bool
    errors: tuple[str, ...]


def normalize_symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        symbols = symbols.replace(",", " ").split()
    result = sorted({str(s).strip().upper() for s in symbols if str(s).strip()})
    if not result:
        raise ValueError("symbols cannot be empty")
    return result


def validate_price_frame(df: pd.DataFrame) -> DataValidationResult:
    errors: list[str] = []
    missing = [c for c in PRICE_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"missing columns: {missing}")
        return DataValidationResult(False, tuple(errors))

    if df.empty:
        errors.append("price data is empty")

    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any():
        errors.append("invalid dates detected")

    if df["symbol"].isna().any():
        errors.append("missing symbols detected")

    for column in ["open", "high", "low", "close", "volume", "value"]:
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.isna().any():
            errors.append(f"non-numeric values in {column}")
        if column != "value" and (numeric < 0).any():
            errors.append(f"negative values in {column}")

    duplicated = df.duplicated(["symbol", "date"]).sum()
    if duplicated:
        errors.append(f"duplicate symbol/date rows: {duplicated}")

    return DataValidationResult(not errors, tuple(errors))
