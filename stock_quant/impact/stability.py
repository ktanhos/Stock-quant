"""Tính ổn định của IC theo thời gian.

IC của cả mẫu chỉ là một con số duy nhất, nó không cho biết một Score giữ được tác
động đều đặn hay chỉ đúng trong vài giai đoạn. Module này trượt một cửa sổ theo thời
gian, tính lại IC trong từng cửa sổ, rồi mô tả xem IC có giữ dấu và giữ độ lớn không.
Không có Score nào bị loại bỏ và không có trọng số nào được sinh ra ở đây.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from stock_quant.consensus.perspectives import PERSPECTIVES_BY_KEY

from .horizons import IMPACT_HORIZONS, forward_return_column, horizon_label
from .ic import score_keys, spearman_ic

DEFAULT_WINDOW = 120
DEFAULT_STEP = 5
MIN_WINDOWS = 3
MIN_WINDOW_LENGTH = 40
# Dưới ngưỡng này thì cửa sổ trượt chỉ còn một vài lát cắt gần như trùng nhau,
# không đủ để nói bất cứ điều gì về tính ổn định theo thời gian.
MIN_ROLLING_OBSERVATIONS = MIN_WINDOW_LENGTH * 2

ROLLING_COLUMNS = (
    "date",
    "score_key",
    "score_name",
    "horizon",
    "horizon_label",
    "ic",
    "symbols",
)

STABILITY_COLUMNS = (
    "score_key",
    "score_name",
    "horizon",
    "horizon_label",
    "windows",
    "mean_ic",
    "ic_std",
    "ic_ir",
    "positive_share",
    "sign_consistency",
    "label",
)


def effective_window(
    observations: int, window: int = DEFAULT_WINDOW, minimum: int = MIN_WINDOW_LENGTH
) -> int:
    """Cửa sổ thực tế, tự co lại khi lịch sử ngắn để vẫn có nhiều hơn một cửa sổ."""
    if observations <= 0:
        return minimum
    return int(max(minimum, min(window, observations // 2)))


def _window_ends(observations: int, window: int, step: int) -> list[int]:
    if observations < window:
        return []
    ends = list(range(window, observations + 1, max(1, step)))
    if ends and ends[-1] != observations:
        ends.append(observations)
    return ends


def rolling_ic_series(
    history: pd.DataFrame,
    score_key: str,
    horizon: int,
    window: int = DEFAULT_WINDOW,
    step: int = DEFAULT_STEP,
    min_pairs: int | None = None,
) -> pd.DataFrame:
    """Chuỗi IC theo thời gian của một Score tại một horizon, cho một mã."""
    column = forward_return_column(horizon)
    if score_key not in history.columns or column not in history.columns:
        return pd.DataFrame(columns=["date", "ic"])

    ordered = history.sort_values("date") if "date" in history.columns else history
    score = ordered[score_key].reset_index(drop=True)
    forward = ordered[column].reset_index(drop=True)
    dates = (
        pd.to_datetime(ordered["date"]).reset_index(drop=True)
        if "date" in ordered.columns
        else pd.Series(range(len(ordered)))
    )

    observations = len(ordered)
    threshold = min_pairs if min_pairs is not None else max(20, window // 4)

    rows = []
    for end in _window_ends(observations, window, step):
        start = end - window
        ic, _, count = spearman_ic(
            score.iloc[start:end], forward.iloc[start:end], min_obs=threshold
        )
        if count < threshold:
            continue
        rows.append({"date": dates.iloc[end - 1], "ic": ic})

    return pd.DataFrame(rows, columns=["date", "ic"])


def rolling_ic(
    df: pd.DataFrame,
    horizons: tuple[int, ...] = IMPACT_HORIZONS,
    window: int = DEFAULT_WINDOW,
    step: int = DEFAULT_STEP,
) -> pd.DataFrame:
    """IC theo thời gian cho mọi Score và mọi horizon.

    Khi có nhiều mã, IC được tính riêng cho từng mã rồi lấy trung bình theo ngày.
    Đây là trung bình của IC giữa các mã, không phải trung bình của Score.
    """
    keys = score_keys(df)
    if not keys:
        return pd.DataFrame(columns=list(ROLLING_COLUMNS))

    groups = (
        list(df.groupby("symbol", sort=True)) if "symbol" in df.columns else [(None, df)]
    )

    frames = []
    for _, history in groups:
        if len(history) < MIN_ROLLING_OBSERVATIONS:
            continue
        span = effective_window(len(history), window)
        for key in keys:
            for horizon in horizons:
                series = rolling_ic_series(history, key, horizon, window=span, step=step)
                if series.empty:
                    continue
                series = series.assign(score_key=key, horizon=horizon)
                frames.append(series)

    if not frames:
        return pd.DataFrame(columns=list(ROLLING_COLUMNS))

    stacked = pd.concat(frames, ignore_index=True)
    merged = stacked.groupby(["score_key", "horizon", "date"], as_index=False).agg(
        ic=("ic", "mean"), symbols=("ic", "count")
    )
    merged["score_name"] = merged["score_key"].map(
        lambda key: PERSPECTIVES_BY_KEY[key].name if key in PERSPECTIVES_BY_KEY else key
    )
    merged["horizon_label"] = merged["horizon"].map(lambda h: horizon_label(int(h)))
    return merged[list(ROLLING_COLUMNS)].sort_values(
        ["score_key", "horizon", "date"]
    ).reset_index(drop=True)


def stability_label(windows: int, sign_consistency: float, ic_ir: float) -> str:
    """Nhãn mô tả mức ổn định, đọc từ dấu và độ phân tán của IC."""
    if windows < MIN_WINDOWS:
        return "Chưa đủ cửa sổ"
    if pd.isna(sign_consistency):
        return "Chưa đủ cửa sổ"
    if sign_consistency >= 0.80 and (not pd.isna(ic_ir) and abs(ic_ir) >= 0.50):
        return "Ổn định"
    if sign_consistency >= 0.65:
        return "Tạm ổn định"
    if sign_consistency >= 0.55:
        return "Dao động"
    return "Đảo dấu"


def ic_stability(rolling: pd.DataFrame) -> pd.DataFrame:
    """Thống kê ổn định của IC cho từng Score và từng horizon."""
    if rolling.empty:
        return pd.DataFrame(columns=list(STABILITY_COLUMNS))

    rows = []
    for (score_key, horizon), group in rolling.groupby(["score_key", "horizon"], sort=False):
        values = group["ic"].dropna()
        windows = len(values)
        mean_ic = float(values.mean()) if windows else np.nan
        ic_std = float(values.std(ddof=1)) if windows > 1 else np.nan
        ic_ir = (
            float(mean_ic / ic_std)
            if windows > 1 and not pd.isna(ic_std) and ic_std > 0
            else np.nan
        )
        positive_share = float((values > 0).mean()) if windows else np.nan
        sign_consistency = (
            np.nan
            if pd.isna(positive_share)
            else float(max(positive_share, 1.0 - positive_share))
        )
        rows.append(
            {
                "score_key": score_key,
                "score_name": PERSPECTIVES_BY_KEY[score_key].name
                if score_key in PERSPECTIVES_BY_KEY
                else score_key,
                "horizon": int(horizon),
                "horizon_label": horizon_label(int(horizon)),
                "windows": windows,
                "mean_ic": mean_ic,
                "ic_std": ic_std,
                "ic_ir": ic_ir,
                "positive_share": positive_share,
                "sign_consistency": sign_consistency,
                "label": stability_label(windows, sign_consistency, ic_ir),
            }
        )
    return pd.DataFrame(rows, columns=list(STABILITY_COLUMNS))


def rolling_chart_frame(rolling: pd.DataFrame, score_key: str) -> pd.DataFrame:
    """Dữ liệu biểu đồ IC theo thời gian của một Score, mỗi horizon một đường."""
    subset = rolling[rolling["score_key"] == score_key]
    if subset.empty:
        return pd.DataFrame()

    wide = subset.pivot_table(index="date", columns="horizon", values="ic", sort=True)
    wide.columns = [f"IC {horizon_label(int(h))}" for h in wide.columns]
    wide.index.name = "Ngày"
    return wide
