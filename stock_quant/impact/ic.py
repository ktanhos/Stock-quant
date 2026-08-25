"""Information Coefficient của từng Score với Future Return.

Mỗi Score được đo riêng lẻ bằng tương quan hạng Spearman với lợi nhuận tương lai.
Tầng này không cộng Score, không trung bình Score và không gán trọng số cho Score.
IC chỉ mô tả mức độ mà một Score đơn lẻ xếp hạng đúng lợi nhuận về sau.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from stock_quant.consensus.perspectives import PERSPECTIVES, PERSPECTIVES_BY_KEY

from .horizons import IMPACT_HORIZONS, forward_return_column, horizon_label

DEFAULT_MIN_OBS = 30

IC_TABLE_COLUMNS = (
    "score_key",
    "score_name",
    "family",
    "role",
    "horizon",
    "horizon_label",
    "ic",
    "p_value",
    "observations",
)


@dataclass(frozen=True)
class ICStat:
    """Kết quả IC của một Score tại một horizon."""

    score_key: str
    horizon: int
    ic: float
    p_value: float
    observations: int

    @property
    def has_value(self) -> bool:
        return not pd.isna(self.ic)


def spearman_ic(
    score: pd.Series, forward_return: pd.Series, min_obs: int = DEFAULT_MIN_OBS
) -> tuple[float, float, int]:
    """Tương quan hạng giữa một Score và Future Return.

    Trả về (ic, p_value, số quan sát). Giá trị NaN khi chưa đủ quan sát hoặc khi
    một trong hai chuỗi gần như không đổi.
    """
    mask = score.notna() & forward_return.notna()
    count = int(mask.sum())
    if count < min_obs:
        return float("nan"), float("nan"), count

    left = score[mask].astype(float)
    right = forward_return[mask].astype(float)
    if left.nunique() < 3 or right.nunique() < 3:
        return float("nan"), float("nan"), count

    result = stats.spearmanr(left, right)
    return float(result.statistic), float(result.pvalue), count


def score_keys(df: pd.DataFrame) -> list[str]:
    """Các Score của 9 mô hình thực sự có mặt và có giá trị trong khung dữ liệu."""
    return [p.key for p in PERSPECTIVES if p.key in df.columns and df[p.key].notna().any()]


def _row(score_key: str, horizon: int, ic: float, p_value: float, observations: int) -> dict:
    perspective = PERSPECTIVES_BY_KEY[score_key]
    return {
        "score_key": score_key,
        "score_name": perspective.name,
        "family": perspective.family,
        "role": perspective.role,
        "horizon": horizon,
        "horizon_label": horizon_label(horizon),
        "ic": ic,
        "p_value": p_value,
        "observations": observations,
    }


def symbol_ic_table(
    history: pd.DataFrame,
    horizons: tuple[int, ...] = IMPACT_HORIZONS,
    min_obs: int = DEFAULT_MIN_OBS,
) -> pd.DataFrame:
    """IC theo chuỗi thời gian của một mã: từng Score với từng horizon."""
    rows = []
    for key in score_keys(history):
        for horizon in horizons:
            column = forward_return_column(horizon)
            if column not in history.columns:
                rows.append(_row(key, horizon, float("nan"), float("nan"), 0))
                continue
            ic, p_value, count = spearman_ic(history[key], history[column], min_obs=min_obs)
            rows.append(_row(key, horizon, ic, p_value, count))
    return pd.DataFrame(rows, columns=list(IC_TABLE_COLUMNS))


def panel_ic_table(
    df: pd.DataFrame,
    horizons: tuple[int, ...] = IMPACT_HORIZONS,
    min_obs: int = DEFAULT_MIN_OBS,
) -> pd.DataFrame:
    """IC trung bình qua các mã, mỗi mã được đo riêng rồi lấy trung bình đơn giản.

    Trung bình ở đây là trung bình của IC giữa các mã, không phải trung bình của
    Score. Không có Score nào được cộng với Score khác.
    """
    if "symbol" not in df.columns:
        return symbol_ic_table(df, horizons=horizons, min_obs=min_obs)

    per_symbol = []
    for symbol, group in df.groupby("symbol", sort=True):
        table = symbol_ic_table(group, horizons=horizons, min_obs=min_obs)
        table.insert(0, "symbol", symbol)
        per_symbol.append(table)

    if not per_symbol:
        return pd.DataFrame(columns=[*IC_TABLE_COLUMNS, "ic_dispersion", "symbols"])

    stacked = pd.concat(per_symbol, ignore_index=True)
    grouped = stacked.groupby(
        ["score_key", "score_name", "family", "role", "horizon", "horizon_label"],
        as_index=False,
        sort=False,
    ).agg(
        ic=("ic", "mean"),
        ic_dispersion=("ic", lambda s: float(s.std(ddof=1)) if s.notna().sum() > 1 else np.nan),
        observations=("observations", "sum"),
        symbols=("ic", "count"),
    )
    grouped["p_value"] = np.nan
    ordered = [*IC_TABLE_COLUMNS, "ic_dispersion", "symbols"]
    return grouped[ordered]


def ic_matrix(table: pd.DataFrame, value: str = "ic") -> pd.DataFrame:
    """Ma trận Score × horizon để hiển thị nhanh."""
    if table.empty:
        return pd.DataFrame()
    wide = table.pivot_table(
        index="score_name", columns="horizon", values=value, sort=False, dropna=False
    )
    wide = wide.reindex(
        [name for name in (p.name for p in PERSPECTIVES) if name in wide.index]
    )
    wide.columns = [horizon_label(int(h)) for h in wide.columns]
    wide.index.name = "Góc nhìn"
    return wide


def ic_strength(ic: float) -> str:
    """Nhãn mô tả độ lớn của IC, không phải trọng số."""
    if ic is None or pd.isna(ic):
        return "—"
    magnitude = abs(float(ic))
    if magnitude >= 0.15:
        return "Rõ"
    if magnitude >= 0.05:
        return "Nhẹ"
    return "Không đáng kể"


def ic_direction(ic: float) -> str:
    if ic is None or pd.isna(ic):
        return "—"
    if ic > 0:
        return "Cùng chiều"
    if ic < 0:
        return "Ngược chiều"
    return "Trung tính"
