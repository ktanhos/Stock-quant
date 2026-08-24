from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_frame(df: pd.DataFrame, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".parquet":
        df.to_parquet(target, index=False)
    elif target.suffix == ".csv":
        df.to_csv(target, index=False)
    else:
        raise ValueError("Use .parquet or .csv")
    return target


def load_frame(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix == ".parquet":
        return pd.read_parquet(source)
    if source.suffix == ".csv":
        return pd.read_csv(source, parse_dates=["date"])
    raise ValueError("Use .parquet or .csv")
