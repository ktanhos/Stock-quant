"""Tổng hợp tầng Score Impact cho một mã hoặc cho cả danh mục đang phân tích.

Tầng này chỉ đo tác động của **từng Score riêng lẻ** lên Future Return. Nó không tạo
Composite Score, không cộng Score, không trung bình Score và không tìm trọng số.
Mọi con số ở đây là kết quả đo lường lịch sử của một mô hình đứng một mình.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from stock_quant.consensus.narrative import format_number, join_names
from stock_quant.consensus.perspectives import PERSPECTIVES_BY_KEY, ROLE_LABELS

from .horizons import IMPACT_HORIZONS, ensure_forward_returns, forward_return_column, horizon_label
from .ic import (
    DEFAULT_MIN_OBS,
    ic_direction,
    ic_matrix,
    ic_strength,
    panel_ic_table,
    score_keys,
    symbol_ic_table,
)
from .quintiles import DEFAULT_BUCKETS, quintile_profile, quintile_summary
from .stability import (
    DEFAULT_STEP,
    DEFAULT_WINDOW,
    effective_window,
    ic_stability,
    rolling_ic,
)

MEANINGFUL_IC = 0.05

IMPACT_DISCLAIMER = (
    "IC và quintile là kết quả đo lường lịch sử của từng mô hình riêng lẻ, "
    "không phải trọng số và không phải khuyến nghị đầu tư."
)

OVERLAP_NOTE = (
    "Future Return 20D và 60D của các phiên liền nhau chồng lấn lên nhau, "
    "nên số quan sát độc lập thấp hơn số dòng và p-value chỉ nên đọc như tham khảo."
)

PURPOSE_NOTE = (
    "Score Impact đo từng mô hình đứng một mình. Không Score nào được cộng với Score "
    "khác và không có trọng số nào được sinh ra ở đây."
)


@dataclass(frozen=True)
class ScoreImpact:
    """Kết quả đo tác động của 9 Score lên Future Return."""

    label: str
    scope: str
    ic: pd.DataFrame
    quintiles: pd.DataFrame
    quintile_spread: pd.DataFrame
    rolling: pd.DataFrame
    stability: pd.DataFrame
    horizons: tuple[int, ...] = IMPACT_HORIZONS
    window: int = DEFAULT_WINDOW
    observations: int = 0
    symbols: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_data(self) -> bool:
        return not self.ic.empty and self.ic["ic"].notna().any()

    @property
    def has_rolling(self) -> bool:
        return not self.rolling.empty

    @property
    def score_keys(self) -> tuple[str, ...]:
        if self.ic.empty:
            return ()
        return tuple(dict.fromkeys(self.ic["score_key"]))

    def ic_matrix(self) -> pd.DataFrame:
        return ic_matrix(self.ic)

    def ic_for(self, score_key: str, horizon: int) -> float:
        rows = self.ic[(self.ic["score_key"] == score_key) & (self.ic["horizon"] == horizon)]
        if rows.empty:
            return float("nan")
        return float(rows.iloc[0]["ic"])


def _observation_count(df: pd.DataFrame, horizons: tuple[int, ...]) -> int:
    keys = score_keys(df)
    columns = [forward_return_column(h) for h in horizons if forward_return_column(h) in df.columns]
    if not keys or not columns:
        return 0
    return int(df[keys + columns].dropna(how="all").shape[0])


def score_impact(
    df: pd.DataFrame,
    symbol: str | None = None,
    horizons: tuple[int, ...] = IMPACT_HORIZONS,
    window: int = DEFAULT_WINDOW,
    step: int = DEFAULT_STEP,
    buckets: int = DEFAULT_BUCKETS,
    min_obs: int = DEFAULT_MIN_OBS,
) -> ScoreImpact:
    """Đo tác động của từng Score lên Future Return.

    Truyền ``symbol`` để đo riêng một mã. Bỏ trống để đo trên toàn bộ danh mục, khi
    đó IC được tính riêng cho từng mã rồi lấy trung bình giữa các mã.
    """
    notes: list[str] = []
    data = df.copy()

    if symbol is not None and "symbol" in data.columns:
        data = data[data["symbol"].str.upper() == symbol.upper()]

    label = symbol.upper() if symbol else "Tất cả mã"
    scope = "symbol" if symbol else "panel"

    symbols = (
        tuple(sorted(str(s) for s in data["symbol"].dropna().unique()))
        if "symbol" in data.columns
        else ()
    )

    empty = pd.DataFrame()
    if data.empty:
        return ScoreImpact(
            label=label,
            scope=scope,
            ic=empty,
            quintiles=empty,
            quintile_spread=empty,
            rolling=empty,
            stability=empty,
            horizons=horizons,
            window=window,
            symbols=symbols,
            notes=("Không có dữ liệu cho phạm vi này.",),
        )

    data = ensure_forward_returns(data, horizons)

    ic = (
        symbol_ic_table(data, horizons=horizons, min_obs=min_obs)
        if scope == "symbol" or len(symbols) <= 1
        else panel_ic_table(data, horizons=horizons, min_obs=min_obs)
    )

    profile = quintile_profile(data, horizons=horizons, buckets=buckets)
    spread = quintile_summary(profile)

    span = effective_window(len(data) if scope == "symbol" else _rows_per_symbol(data), window)
    rolling = rolling_ic(data, horizons=horizons, window=window, step=step)
    stability = ic_stability(rolling)

    observations = _observation_count(data, horizons)

    if ic.empty or not ic["ic"].notna().any():
        notes.append(
            "Lịch sử hiện tại chưa đủ dài để đo IC. "
            f"Cần ít nhất {min_obs} phiên có đồng thời Score và Future Return."
        )
    if profile.empty:
        notes.append("Chưa đủ quan sát để chia Score thành 5 nhóm quintile.")
    if rolling.empty:
        notes.append(
            "Chưa đủ lịch sử để trượt cửa sổ IC theo thời gian, "
            f"cần khoảng {span * 2} phiên trở lên."
        )
    notes.append(OVERLAP_NOTE)
    notes.append(PURPOSE_NOTE)

    return ScoreImpact(
        label=label,
        scope=scope,
        ic=ic,
        quintiles=profile,
        quintile_spread=spread,
        rolling=rolling,
        stability=stability,
        horizons=horizons,
        window=span,
        observations=observations,
        symbols=symbols,
        notes=tuple(notes),
    )


def _rows_per_symbol(df: pd.DataFrame) -> int:
    if "symbol" not in df.columns:
        return len(df)
    counts = df.groupby("symbol").size()
    return int(counts.min()) if not counts.empty else 0


def impact_table(impact: ScoreImpact, horizon: int) -> pd.DataFrame:
    """Bảng đọc nhanh cho một horizon: IC, quintile spread và mức ổn định."""
    if impact.ic.empty:
        return pd.DataFrame()

    ic_rows = impact.ic[impact.ic["horizon"] == horizon]
    if ic_rows.empty:
        return pd.DataFrame()

    spread = (
        impact.quintile_spread[impact.quintile_spread["horizon"] == horizon]
        .set_index("score_key")
        if not impact.quintile_spread.empty
        else pd.DataFrame()
    )
    stability = (
        impact.stability[impact.stability["horizon"] == horizon].set_index("score_key")
        if not impact.stability.empty
        else pd.DataFrame()
    )

    rows = []
    for _, row in ic_rows.iterrows():
        key = row["score_key"]
        rows.append(
            {
                "Góc nhìn": row["score_name"],
                "Vai trò": ROLE_LABELS.get(row["role"], row["role"]),
                "IC": None if pd.isna(row["ic"]) else round(float(row["ic"]), 3),
                "Mức tác động": ic_strength(row["ic"]),
                "Chiều": ic_direction(row["ic"]),
                "Q5 − Q1 (%)": (
                    round(float(spread.loc[key, "spread"]) * 100.0, 2)
                    if key in spread.index and pd.notna(spread.loc[key, "spread"])
                    else None
                ),
                "Đơn điệu": (
                    round(float(spread.loc[key, "monotonicity"]), 2)
                    if key in spread.index and pd.notna(spread.loc[key, "monotonicity"])
                    else None
                ),
                "Ổn định": (
                    str(stability.loc[key, "label"]) if key in stability.index else "—"
                ),
                "Số quan sát": int(row["observations"]),
            }
        )
    return pd.DataFrame(rows)


def stability_table(impact: ScoreImpact, horizon: int) -> pd.DataFrame:
    """Bảng ổn định IC theo thời gian cho một horizon."""
    if impact.stability.empty:
        return pd.DataFrame()
    rows = impact.stability[impact.stability["horizon"] == horizon]
    if rows.empty:
        return pd.DataFrame()

    order = {key: index for index, key in enumerate(PERSPECTIVES_BY_KEY)}
    rows = rows.sort_values("score_key", key=lambda s: s.map(order))

    return pd.DataFrame(
        {
            "Góc nhìn": rows["score_name"].to_numpy(),
            "Số cửa sổ": rows["windows"].to_numpy(),
            "IC trung bình": rows["mean_ic"].round(3).to_numpy(),
            "Độ lệch chuẩn IC": rows["ic_std"].round(3).to_numpy(),
            "IC / Độ lệch": rows["ic_ir"].round(2).to_numpy(),
            "Tỉ lệ cửa sổ IC dương": rows["positive_share"].round(2).to_numpy(),
            "Giữ dấu": rows["sign_consistency"].round(2).to_numpy(),
            "Kết luận": rows["label"].to_numpy(),
        }
    )


def quintile_display(impact: ScoreImpact, score_key: str, horizon: int) -> pd.DataFrame:
    """Bảng quintile của một Score tại một horizon."""
    if impact.quintiles.empty:
        return pd.DataFrame()
    rows = impact.quintiles[
        (impact.quintiles["score_key"] == score_key) & (impact.quintiles["horizon"] == horizon)
    ].sort_values("bucket")
    if rows.empty:
        return pd.DataFrame()

    return pd.DataFrame(
        {
            "Nhóm": rows["bucket_label"].to_numpy(),
            "Score trung bình": rows["mean_score"].round(1).to_numpy(),
            "Future Return trung bình (%)": (rows["mean_return"] * 100).round(2).to_numpy(),
            "Future Return trung vị (%)": (rows["median_return"] * 100).round(2).to_numpy(),
            "Tỉ lệ phiên dương": rows["hit_rate"].round(2).to_numpy(),
            "Số quan sát": rows["observations"].to_numpy(),
        }
    )


def _stability_for(impact: ScoreImpact, score_key: str, horizon: int) -> str:
    if impact.stability.empty:
        return ""
    rows = impact.stability[
        (impact.stability["score_key"] == score_key) & (impact.stability["horizon"] == horizon)
    ]
    if rows.empty:
        return ""
    return str(rows.iloc[0]["label"])


def impact_highlights(impact: ScoreImpact, threshold: float = MEANINGFUL_IC) -> list[str]:
    """Vài câu đọc nhanh về Score nào đang có tác động đo được ở từng horizon."""
    if not impact.has_data:
        return [
            "Chưa đủ dữ liệu để đo tác động của Score lên Future Return.",
            IMPACT_DISCLAIMER,
        ]

    lines: list[str] = []
    for horizon in impact.horizons:
        rows = impact.ic[(impact.ic["horizon"] == horizon) & impact.ic["ic"].notna()].copy()
        label = horizon_label(horizon)
        if rows.empty:
            lines.append(f"{label}: chưa đo được IC cho Score nào.")
            continue

        rows["magnitude"] = rows["ic"].abs()
        strong = rows[rows["magnitude"] >= threshold].sort_values("magnitude", ascending=False)
        if strong.empty:
            best = rows.sort_values("magnitude", ascending=False).iloc[0]
            lines.append(
                f"{label}: không Score nào đạt |IC| {format_number(threshold)}. "
                f"Cao nhất là {best['score_name']} với IC {format_number(float(best['ic']))}."
            )
            continue

        parts = []
        for _, row in strong.head(3).iterrows():
            note = _stability_for(impact, row["score_key"], horizon)
            direction = "cùng chiều" if float(row["ic"]) > 0 else "ngược chiều"
            suffix = f", {note.lower()}" if note and note != "—" else ""
            parts.append(
                f"{row['score_name']} IC {format_number(float(row['ic']))} ({direction}{suffix})"
            )
        lines.append(f"{label}: " + join_names(parts) + ".")

    lines.append(IMPACT_DISCLAIMER)
    return lines


def impact_overview(impacts: list[ScoreImpact], threshold: float = MEANINGFUL_IC) -> pd.DataFrame:
    """Bảng tổng quan nhiều mã: Score có |IC| lớn nhất ở từng horizon."""
    rows = []
    for impact in impacts:
        row: dict[str, object] = {"Phạm vi": impact.label, "Số quan sát": impact.observations}
        for horizon in impact.horizons:
            column = f"IC {horizon_label(horizon)} cao nhất"
            if impact.ic.empty:
                row[column] = "—"
                continue
            candidates = impact.ic[
                (impact.ic["horizon"] == horizon) & impact.ic["ic"].notna()
            ]
            if candidates.empty:
                row[column] = "—"
                continue
            best = candidates.loc[candidates["ic"].abs().idxmax()]
            value = float(best["ic"])
            if abs(value) < threshold:
                row[column] = "Không đáng kể"
            else:
                row[column] = f"{best['score_name']} ({format_number(value)})"
        rows.append(row)
    return pd.DataFrame(rows)


def perspective_name(score_key: str) -> str:
    perspective = PERSPECTIVES_BY_KEY.get(score_key)
    return perspective.name if perspective else score_key
