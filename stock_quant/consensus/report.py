"""Consensus Analysis: đọc 9 góc nhìn độc lập và mô tả cấu trúc đồng thuận.

Nguyên tắc của module này:

* Không tạo Composite Score.
* Không cộng, không trung bình, không gán trọng số cho 9 Score.
* Chỉ đếm và phân nhóm các góc nhìn, rồi mô tả bằng ngôn ngữ tự nhiên.

Các con số duy nhất được tạo ra ở đây là số lượng góc nhìn trong từng nhóm.
Chúng là thống kê về mức độ đồng thuận, không phải điểm đánh giá cổ phiếu.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from .narrative import build_narrative, join_names as _join
from .overlap import (
    DEFAULT_OVERLAP_THRESHOLD,
    OverlapReport,
    analyze_overlap,
    cluster_of,
)
from .perspectives import (
    CONTEXT,
    DIRECTIONAL,
    NEGATIVE,
    NEUTRAL,
    POSITIVE,
    PERSPECTIVES,
    RISK,
    ROLE_LABELS,
    ROLE_ORDER,
    UNAVAILABLE,
    Perspective,
    strength_label,
)

CONSENSUS_LABELS = {
    "consensus_up": "Đồng thuận tăng",
    "lean_up": "Nghiêng về tăng",
    "consensus_down": "Đồng thuận giảm",
    "lean_down": "Nghiêng về giảm",
    "conflict": "Mâu thuẫn",
    "neutral": "Trung tính",
    "insufficient": "Chưa đủ dữ liệu",
}


@dataclass(frozen=True)
class ViewStance:
    """Trạng thái của một góc nhìn tại phiên gần nhất."""

    perspective: Perspective
    score: float | None
    stance: str
    reading: str
    strength: str
    cluster: int | None = None

    @property
    def key(self) -> str:
        return self.perspective.key

    @property
    def name(self) -> str:
        return self.perspective.name

    @property
    def family(self) -> str:
        return self.perspective.family

    @property
    def role(self) -> str:
        return self.perspective.role

    @property
    def available(self) -> bool:
        return self.stance != UNAVAILABLE


@dataclass(frozen=True)
class ConsensusGroup:
    """Một nhóm góc nhìn đang nói cùng một điều."""

    label: str
    stance: str
    role: str
    members: tuple[ViewStance, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(view.name for view in self.members)

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass(frozen=True)
class ConflictNote:
    """Một mâu thuẫn cụ thể giữa các góc nhìn."""

    kind: str
    message: str
    members: tuple[str, ...] = ()


@dataclass(frozen=True)
class SymbolConsensus:
    """Toàn bộ kết quả Consensus Analysis của một mã."""

    symbol: str
    date: pd.Timestamp | None
    views: tuple[ViewStance, ...]
    directional_counts: dict[str, int]
    consensus_state: str
    agreement_groups: tuple[ConsensusGroup, ...]
    conflicts: tuple[ConflictNote, ...]
    neutral_views: tuple[ViewStance, ...]
    overlap: OverlapReport
    narrative: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def consensus_label(self) -> str:
        return CONSENSUS_LABELS.get(self.consensus_state, self.consensus_state)

    def views_by_role(self, role: str) -> tuple[ViewStance, ...]:
        return tuple(view for view in self.views if view.role == role)

    def view(self, key: str) -> ViewStance | None:
        for item in self.views:
            if item.key == key:
                return item
        return None

    @property
    def available_views(self) -> tuple[ViewStance, ...]:
        return tuple(view for view in self.views if view.available)


def _latest_row(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    ordered = df.sort_values("date") if "date" in df.columns else df
    return ordered.iloc[-1]


def _build_views(row: pd.Series, overlap: OverlapReport) -> tuple[ViewStance, ...]:
    views = []
    for perspective in PERSPECTIVES:
        raw = row.get(perspective.key) if perspective.key in row.index else None
        stance = perspective.stance(raw)
        score = None if stance == UNAVAILABLE else float(raw)
        views.append(
            ViewStance(
                perspective=perspective,
                score=score,
                stance=stance,
                reading=perspective.reading(stance),
                strength=strength_label(score),
                cluster=cluster_of(overlap, perspective.key),
            )
        )
    return tuple(views)


def _directional_state(counts: dict[str, int]) -> str:
    up = counts["up"]
    down = counts["down"]
    total = counts["up"] + counts["down"] + counts["neutral"]

    if total == 0:
        return "insufficient"
    if up and down:
        return "conflict"
    if up:
        return "consensus_up" if up > total - up else "lean_up"
    if down:
        return "consensus_down" if down > total - down else "lean_down"
    return "neutral"


def _agreement_groups(views: tuple[ViewStance, ...]) -> tuple[ConsensusGroup, ...]:
    groups: list[ConsensusGroup] = []

    directional = [v for v in views if v.role == DIRECTIONAL and v.available]
    for stance, label in ((POSITIVE, "Đồng thuận hướng tăng"), (NEGATIVE, "Đồng thuận hướng giảm")):
        members = tuple(v for v in directional if v.stance == stance)
        if len(members) >= 2:
            groups.append(ConsensusGroup(label, stance, DIRECTIONAL, members))

    context = [v for v in views if v.role == CONTEXT and v.available]
    for stance, label in (
        (POSITIVE, "Bối cảnh mở rộng và có quán tính"),
        (NEGATIVE, "Bối cảnh co hẹp và hay đảo chiều"),
    ):
        members = tuple(v for v in context if v.stance == stance)
        if len(members) >= 2:
            groups.append(ConsensusGroup(label, stance, CONTEXT, members))

    risk = [v for v in views if v.role == RISK and v.available]
    warnings = tuple(v for v in risk if v.perspective.is_unfavorable(v.stance))
    if len(warnings) >= 2:
        groups.append(ConsensusGroup("Đồng thuận cảnh báo rủi ro", NEGATIVE, RISK, warnings))
    calm = tuple(v for v in risk if v.perspective.is_favorable(v.stance))
    if len(calm) >= 2:
        groups.append(ConsensusGroup("Đồng thuận rủi ro trong tầm kiểm soát", POSITIVE, RISK, calm))

    return tuple(groups)


def _conflicts(views: tuple[ViewStance, ...]) -> tuple[ConflictNote, ...]:
    notes: list[ConflictNote] = []
    by_key = {v.key: v for v in views}

    directional = [v for v in views if v.role == DIRECTIONAL and v.available]
    bullish = [v for v in directional if v.stance == POSITIVE]
    bearish = [v for v in directional if v.stance == NEGATIVE]

    if bullish and bearish:
        notes.append(
            ConflictNote(
                kind="directional",
                message=(
                    f"{_join(v.name for v in bullish)} nghiêng về tăng "
                    f"trong khi {_join(v.name for v in bearish)} nghiêng về giảm"
                ),
                members=tuple(v.name for v in bullish) + tuple(v.name for v in bearish),
            )
        )

    trend = by_key.get("vrh_score")
    momentum = by_key.get("tsm_score")
    if (
        trend is not None
        and momentum is not None
        and trend.stance == NEGATIVE
        and momentum.stance in (POSITIVE, NEGATIVE)
    ):
        notes.append(
            ConflictNote(
                kind="persistence",
                message=(
                    f"{momentum.name} ghi nhận {momentum.reading.lower()} "
                    f"nhưng {trend.name} cho thấy chuỗi giá hay đảo chiều, "
                    "nên đà hiện tại thiếu quán tính"
                ),
                members=(momentum.name, trend.name),
            )
        )

    expansion = by_key.get("exp_score")
    volatility = by_key.get("vsf_score")
    if (
        expansion is not None
        and volatility is not None
        and expansion.stance == POSITIVE
        and volatility.stance == POSITIVE
    ):
        notes.append(
            ConflictNote(
                kind="expansion_risk",
                message=(
                    "Biên độ mở rộng đi kèm biến động cao hơn nền 60 phiên, "
                    "phần mở rộng này đến từ rủi ro chứ chưa chắc từ hướng giá"
                ),
                members=(expansion.name, volatility.name),
            )
        )

    risk_warnings = [
        v for v in views if v.role == RISK and v.available and v.perspective.is_unfavorable(v.stance)
    ]
    if bullish and risk_warnings:
        names = _join(v.name for v in risk_warnings)
        notes.append(
            ConflictNote(
                kind="direction_vs_risk",
                message=(
                    f"Có {len(bullish)} góc nhìn hướng giá nghiêng về tăng "
                    f"nhưng {names} chưa xác nhận về mặt rủi ro"
                ),
                members=tuple(v.name for v in bullish) + tuple(v.name for v in risk_warnings),
            )
        )

    integrity = by_key.get("man_score")
    if integrity is not None and integrity.stance == NEGATIVE:
        notes.append(
            ConflictNote(
                kind="integrity",
                message=(
                    "Manipulation Guard ghi nhận giao dịch bất thường, "
                    "các góc nhìn dựa trên giá và khối lượng cần được đọc thận trọng hơn"
                ),
                members=(integrity.name,),
            )
        )

    return tuple(notes)


def analyze_symbol(
    history: pd.DataFrame,
    symbol: str,
    overlap_threshold: float = DEFAULT_OVERLAP_THRESHOLD,
    min_periods: int = 20,
    panel_overlap: OverlapReport | None = None,
) -> SymbolConsensus:
    """Consensus Analysis cho một mã, dựa trên lịch sử Score của chính mã đó."""
    notes: list[str] = []
    overlap = analyze_overlap(history, threshold=overlap_threshold, min_periods=min_periods)

    if not overlap.has_data and panel_overlap is not None and panel_overlap.has_data:
        overlap = panel_overlap
        notes.append(
            "Lịch sử của mã chưa đủ để đo thông tin chung, "
            "tương quan được lấy từ toàn bộ danh mục đang phân tích."
        )
    elif not overlap.has_data:
        notes.append("Chưa đủ quan sát để đo mức độ thông tin chung giữa các góc nhìn.")

    row = _latest_row(history)
    if row is None:
        return SymbolConsensus(
            symbol=symbol,
            date=None,
            views=(),
            directional_counts={"up": 0, "down": 0, "neutral": 0, "unavailable": len(PERSPECTIVES)},
            consensus_state="insufficient",
            agreement_groups=(),
            conflicts=(),
            neutral_views=(),
            overlap=overlap,
            narrative="Không có dữ liệu cho mã này.",
            notes=tuple(notes),
        )

    views = _build_views(row, overlap)

    directional = [v for v in views if v.role == DIRECTIONAL]
    counts = {
        "up": sum(1 for v in directional if v.stance == POSITIVE),
        "down": sum(1 for v in directional if v.stance == NEGATIVE),
        "neutral": sum(1 for v in directional if v.stance == NEUTRAL),
        "unavailable": sum(1 for v in directional if v.stance == UNAVAILABLE),
    }

    missing = [v.name for v in views if not v.available]
    if missing:
        notes.append("Chưa đủ lịch sử cho: " + ", ".join(missing) + ".")

    unmeasured = [v.name for v in views if v.available and v.cluster is None]
    if unmeasured and overlap.has_data:
        notes.append(
            "Chưa đo được thông tin chung cho: "
            + ", ".join(unmeasured)
            + ". Các góc nhìn này vẫn được giữ nguyên trong phân tích."
        )

    state = _directional_state(counts)
    groups = _agreement_groups(views)
    conflicts = _conflicts(views)
    neutral_views = tuple(v for v in views if v.stance == NEUTRAL)

    date = row.get("date") if "date" in row.index else None

    consensus = SymbolConsensus(
        symbol=symbol,
        date=pd.Timestamp(date) if date is not None and pd.notna(date) else None,
        views=views,
        directional_counts=counts,
        consensus_state=state,
        agreement_groups=groups,
        conflicts=conflicts,
        neutral_views=neutral_views,
        overlap=overlap,
        notes=tuple(notes),
    )
    return replace(consensus, narrative=build_narrative(consensus))


def consensus_report(
    df: pd.DataFrame,
    symbols: list[str] | None = None,
    overlap_threshold: float = DEFAULT_OVERLAP_THRESHOLD,
    min_periods: int = 20,
) -> list[SymbolConsensus]:
    """Consensus Analysis cho một hoặc nhiều mã."""
    if df.empty:
        return []

    data = df.copy()
    if symbols:
        wanted = {s.upper() for s in symbols}
        data = data[data["symbol"].str.upper().isin(wanted)]
    if data.empty:
        return []

    panel_overlap = analyze_overlap(
        data,
        threshold=overlap_threshold,
        min_periods=min_periods,
        basis="panel",
    )

    reports = []
    for symbol, group in data.groupby("symbol", sort=True):
        reports.append(
            analyze_symbol(
                group,
                str(symbol),
                overlap_threshold=overlap_threshold,
                min_periods=min_periods,
                panel_overlap=panel_overlap,
            )
        )
    return reports


def views_table(consensus: SymbolConsensus) -> pd.DataFrame:
    """Bảng 9 góc nhìn để hiển thị nhanh."""
    rows = []
    for role in ROLE_ORDER:
        for view in consensus.views_by_role(role):
            rows.append(
                {
                    "Vai trò": ROLE_LABELS[role],
                    "Góc nhìn": view.name,
                    "Nhóm": view.family,
                    "Score": round(view.score, 1) if view.score is not None else None,
                    "Diễn giải": view.reading,
                    "Mức độ": view.strength,
                    "Nhóm thông tin": f"Nhóm {view.cluster}" if view.cluster else "—",
                }
            )
    return pd.DataFrame(rows)


def consensus_overview(reports: list[SymbolConsensus]) -> pd.DataFrame:
    """Bảng tổng quan nhiều mã, chỉ chứa số đếm góc nhìn, không có điểm tổng hợp."""
    rows = []
    for report in reports:
        counts = report.directional_counts
        risk_warnings = [
            v.name
            for v in report.views_by_role(RISK)
            if v.available and v.perspective.is_unfavorable(v.stance)
        ]
        rows.append(
            {
                "Mã": report.symbol,
                "Ngày": report.date.date() if report.date is not None else None,
                "Trạng thái": report.consensus_label,
                "Hướng tăng": counts["up"],
                "Hướng giảm": counts["down"],
                "Trung tính": counts["neutral"],
                "Mâu thuẫn": len(report.conflicts),
                "Cảnh báo rủi ro": ", ".join(risk_warnings) if risk_warnings else "—",
                "Nhóm thông tin / Góc nhìn đo được": (
                    f"{report.overlap.independent_groups}/{report.overlap.views_covered}"
                    if report.overlap.has_data
                    else "—"
                ),
            }
        )
    return pd.DataFrame(rows)
