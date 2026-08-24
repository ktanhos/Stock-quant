"""Đo mức độ thông tin chung giữa các góc nhìn bằng correlation.

Correlation ở đây chỉ dùng để biết hai góc nhìn đang nói cùng một câu chuyện đến
mức nào. Không có mô hình nào bị loại bỏ tự động vì tương quan cao.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .perspectives import PERSPECTIVES_BY_KEY, SCORE_KEYS

DEFAULT_OVERLAP_THRESHOLD = 0.70


@dataclass(frozen=True)
class OverlapReport:
    """Kết quả phân tích thông tin chung giữa các góc nhìn."""

    correlation: pd.DataFrame
    clusters: tuple[tuple[str, ...], ...] = ()
    pairs: pd.DataFrame = field(default_factory=pd.DataFrame)
    basis: str = "symbol"
    observations: int = 0
    threshold: float = DEFAULT_OVERLAP_THRESHOLD

    @property
    def views_covered(self) -> int:
        return sum(len(c) for c in self.clusters)

    @property
    def independent_groups(self) -> int:
        return len(self.clusters)

    @property
    def shared_clusters(self) -> tuple[tuple[str, ...], ...]:
        return tuple(c for c in self.clusters if len(c) > 1)

    @property
    def has_data(self) -> bool:
        return bool(self.clusters)


def available_score_columns(df: pd.DataFrame) -> list[str]:
    """Các cột Score của 9 góc nhìn thực sự có mặt và có giá trị."""
    return [key for key in SCORE_KEYS if key in df.columns and df[key].notna().any()]


def score_correlation(df: pd.DataFrame, min_periods: int = 20) -> pd.DataFrame:
    """Ma trận tương quan giữa các Score, giữ nguyên toàn bộ góc nhìn có dữ liệu."""
    columns = available_score_columns(df)
    if not columns:
        return pd.DataFrame()
    return df[columns].corr(min_periods=min_periods)


def overlap_pairs(corr: pd.DataFrame, threshold: float = DEFAULT_OVERLAP_THRESHOLD) -> pd.DataFrame:
    """Các cặp góc nhìn chia sẻ phần lớn thông tin."""
    columns = ["model_a", "model_b", "correlation", "abs_correlation"]
    rows: list[dict[str, object]] = []
    names = list(corr.columns)

    for i, left in enumerate(names):
        for right in names[i + 1:]:
            value = corr.loc[left, right]
            if pd.isna(value) or abs(float(value)) < threshold:
                continue
            rows.append(
                {
                    "model_a": PERSPECTIVES_BY_KEY[left].name if left in PERSPECTIVES_BY_KEY else left,
                    "model_b": PERSPECTIVES_BY_KEY[right].name if right in PERSPECTIVES_BY_KEY else right,
                    "correlation": float(value),
                    "abs_correlation": abs(float(value)),
                }
            )

    pairs = pd.DataFrame(rows, columns=columns)
    if pairs.empty:
        return pairs
    return pairs.sort_values("abs_correlation", ascending=False).reset_index(drop=True)


def information_clusters(
    corr: pd.DataFrame,
    threshold: float = DEFAULT_OVERLAP_THRESHOLD,
) -> tuple[tuple[str, ...], ...]:
    """Gom các góc nhìn có |correlation| vượt ngưỡng vào cùng một nhóm thông tin.

    Mọi góc nhìn đều nằm trong đúng một nhóm. Nhóm chỉ nói lên rằng các thành viên
    đang mang thông tin gần giống nhau, không phải là lý do để bỏ bớt mô hình.
    """
    names = list(corr.columns)
    if not names:
        return ()

    parent = {name: name for name in names}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i, left in enumerate(names):
        for right in names[i + 1:]:
            value = corr.loc[left, right]
            if pd.notna(value) and abs(float(value)) >= threshold:
                union(left, right)

    grouped: dict[str, list[str]] = {}
    for name in names:
        grouped.setdefault(find(name), []).append(name)

    ordered = sorted(grouped.values(), key=lambda group: (-len(group), names.index(group[0])))
    return tuple(tuple(group) for group in ordered)


def analyze_overlap(
    df: pd.DataFrame,
    threshold: float = DEFAULT_OVERLAP_THRESHOLD,
    min_periods: int = 20,
    basis: str = "symbol",
) -> OverlapReport:
    """Phân tích thông tin chung cho một panel Score."""
    corr = score_correlation(df, min_periods=min_periods)
    if corr.empty:
        return OverlapReport(correlation=corr, basis=basis, observations=len(df), threshold=threshold)

    usable = [c for c in corr.columns if corr[c].notna().any()]
    corr = corr.loc[usable, usable]
    if corr.empty:
        return OverlapReport(correlation=corr, basis=basis, observations=len(df), threshold=threshold)

    return OverlapReport(
        correlation=corr,
        clusters=information_clusters(corr, threshold),
        pairs=overlap_pairs(corr, threshold),
        basis=basis,
        observations=int(df[usable].dropna(how="all").shape[0]),
        threshold=threshold,
    )


def cluster_of(report: OverlapReport, key: str) -> int | None:
    """Chỉ số nhóm thông tin của một góc nhìn, đếm từ 1."""
    for index, cluster in enumerate(report.clusters, start=1):
        if key in cluster:
            return index
    return None
