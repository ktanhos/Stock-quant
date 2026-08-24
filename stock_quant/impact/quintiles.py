"""Quintile analysis: chia từng Score thành 5 nhóm và đọc Future Return trung bình.

Mỗi Score được chia nhóm độc lập với các Score khác. Không có Score nào được cộng
hay gán trọng số. Bảng quintile chỉ trả lời một câu hỏi: khi Score của chính mô hình
đó ở nhóm cao hay nhóm thấp thì lợi nhuận về sau trung bình là bao nhiêu.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from stock_quant.consensus.perspectives import PERSPECTIVES_BY_KEY

from .horizons import IMPACT_HORIZONS, forward_return_column, horizon_label
from .ic import score_keys

DEFAULT_BUCKETS = 5
MIN_ROWS_PER_BUCKET = 4

PROFILE_COLUMNS = (
    "score_key",
    "score_name",
    "horizon",
    "horizon_label",
    "bucket",
    "bucket_label",
    "observations",
    "mean_score",
    "mean_return",
    "median_return",
    "hit_rate",
)

SUMMARY_COLUMNS = (
    "score_key",
    "score_name",
    "horizon",
    "horizon_label",
    "low_return",
    "high_return",
    "spread",
    "monotonicity",
    "observations",
)


def bucket_label(bucket: int, buckets: int = DEFAULT_BUCKETS) -> str:
    if bucket == 1:
        return "Q1 (Score thấp nhất)"
    if bucket == buckets:
        return f"Q{buckets} (Score cao nhất)"
    return f"Q{bucket}"


def assign_buckets(score: pd.Series, buckets: int = DEFAULT_BUCKETS) -> pd.Series:
    """Chia một Score thành các nhóm phân vị bằng nhau, đánh số từ 1.

    Xếp hạng trước khi chia để Score có nhiều giá trị trùng nhau vẫn tách được nhóm.
    """
    values = score.dropna()
    result = pd.Series(np.nan, index=score.index, dtype="float64")
    if len(values) < buckets * MIN_ROWS_PER_BUCKET or values.nunique() < buckets:
        return result

    ranks = values.rank(method="first")
    labels = pd.qcut(ranks, buckets, labels=False)
    result.loc[values.index] = np.asarray(labels, dtype="float64") + 1.0
    return result


def _bucketed_frame(
    df: pd.DataFrame, score_key: str, horizon: int, buckets: int
) -> pd.DataFrame:
    column = forward_return_column(horizon)
    if score_key not in df.columns or column not in df.columns:
        return pd.DataFrame(columns=["bucket", "score", "forward"])

    columns = [score_key, column] + (["symbol"] if "symbol" in df.columns else [])
    data = df[columns].dropna(subset=[score_key, column]).copy()
    if data.empty:
        return pd.DataFrame(columns=["bucket", "score", "forward"])

    # Chia nhóm trong nội bộ từng mã để mức Score của mã này không lấn sang mã khác.
    if "symbol" in data.columns:
        data["bucket"] = data.groupby("symbol", group_keys=False)[score_key].apply(
            lambda s: assign_buckets(s, buckets)
        )
    else:
        data["bucket"] = assign_buckets(data[score_key], buckets)

    data = data.dropna(subset=["bucket"])
    if data.empty:
        return pd.DataFrame(columns=["bucket", "score", "forward"])

    return pd.DataFrame(
        {
            "bucket": data["bucket"].astype(int),
            "score": data[score_key].astype(float),
            "forward": data[column].astype(float),
        }
    )


def quintile_table(
    df: pd.DataFrame,
    score_key: str,
    horizon: int,
    buckets: int = DEFAULT_BUCKETS,
) -> pd.DataFrame:
    """Future Return trung bình theo từng nhóm Score của một mô hình."""
    bucketed = _bucketed_frame(df, score_key, horizon, buckets)
    if bucketed.empty:
        return pd.DataFrame(columns=list(PROFILE_COLUMNS))

    grouped = bucketed.groupby("bucket", as_index=False).agg(
        observations=("forward", "size"),
        mean_score=("score", "mean"),
        mean_return=("forward", "mean"),
        median_return=("forward", "median"),
        hit_rate=("forward", lambda s: float((s > 0).mean())),
    )

    perspective = PERSPECTIVES_BY_KEY[score_key]
    grouped.insert(0, "score_key", score_key)
    grouped.insert(1, "score_name", perspective.name)
    grouped.insert(2, "horizon", horizon)
    grouped.insert(3, "horizon_label", horizon_label(horizon))
    grouped["bucket_label"] = grouped["bucket"].map(lambda b: bucket_label(int(b), buckets))
    return grouped[list(PROFILE_COLUMNS)].sort_values("bucket").reset_index(drop=True)


def quintile_profile(
    df: pd.DataFrame,
    horizons: tuple[int, ...] = IMPACT_HORIZONS,
    buckets: int = DEFAULT_BUCKETS,
) -> pd.DataFrame:
    """Bảng quintile cho toàn bộ Score đang có và toàn bộ horizon."""
    frames = [
        quintile_table(df, key, horizon, buckets=buckets)
        for key in score_keys(df)
        for horizon in horizons
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=list(PROFILE_COLUMNS))
    return pd.concat(frames, ignore_index=True)


def quintile_summary(profile: pd.DataFrame) -> pd.DataFrame:
    """Chênh lệch nhóm cao trừ nhóm thấp và mức đơn điệu của từng Score."""
    if profile.empty:
        return pd.DataFrame(columns=list(SUMMARY_COLUMNS))

    rows = []
    for (score_key, horizon), group in profile.groupby(["score_key", "horizon"], sort=False):
        ordered = group.sort_values("bucket")
        low = float(ordered.iloc[0]["mean_return"])
        high = float(ordered.iloc[-1]["mean_return"])
        if len(ordered) >= 3 and ordered["mean_return"].nunique() > 1:
            monotonicity = float(
                stats.spearmanr(ordered["bucket"], ordered["mean_return"]).statistic
            )
        else:
            monotonicity = float("nan")
        rows.append(
            {
                "score_key": score_key,
                "score_name": ordered.iloc[0]["score_name"],
                "horizon": int(horizon),
                "horizon_label": horizon_label(int(horizon)),
                "low_return": low,
                "high_return": high,
                "spread": high - low,
                "monotonicity": monotonicity,
                "observations": int(ordered["observations"].sum()),
            }
        )
    return pd.DataFrame(rows, columns=list(SUMMARY_COLUMNS))


def quintile_chart_frame(profile: pd.DataFrame, score_key: str) -> pd.DataFrame:
    """Dữ liệu biểu đồ Score → Future Return: nhóm Score trên trục ngang."""
    subset = profile[profile["score_key"] == score_key]
    if subset.empty:
        return pd.DataFrame()

    wide = subset.pivot_table(
        index="bucket", columns="horizon", values="mean_return", sort=True
    )
    wide.columns = [f"Future Return {horizon_label(int(h))}" for h in wide.columns]
    wide.index = [f"Q{int(b)}" for b in wide.index]
    wide.index.name = "Nhóm Score"
    return wide * 100.0
