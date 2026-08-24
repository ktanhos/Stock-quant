"""Market Narrative: giải thích ngắn gọn vì sao các góc nhìn đang đồng thuận hoặc mâu thuẫn.

Phần tường thuật được sinh từ chính trạng thái của 9 góc nhìn. Nó mô tả cấu trúc
đồng thuận, không tạo ra điểm số mới và không đưa ra khuyến nghị mua bán.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .perspectives import CONTEXT, DIRECTIONAL, NEGATIVE, POSITIVE, RISK

if TYPE_CHECKING:  # pragma: no cover
    from .report import SymbolConsensus

MAX_CONFLICT_SENTENCES = 2


def format_number(value: float, digits: int = 2) -> str:
    """Định dạng số theo quy ước dấu phẩy thập phân."""
    return f"{value:.{digits}f}".replace(".", ",")


def join_names(names) -> str:
    """Nối danh sách tên theo văn phong tiếng Việt."""
    names = list(names)
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " và " + names[-1]


def _directional_sentence(consensus: "SymbolConsensus") -> str:
    counts = consensus.directional_counts
    total = counts["up"] + counts["down"] + counts["neutral"]
    if total == 0:
        return "Chưa góc nhìn hướng giá nào có đủ lịch sử để đọc."

    up = [v.name for v in consensus.views_by_role(DIRECTIONAL) if v.stance == POSITIVE]
    down = [v.name for v in consensus.views_by_role(DIRECTIONAL) if v.stance == NEGATIVE]
    flat = [v.name for v in consensus.views_by_role(DIRECTIONAL) if v.stance not in (POSITIVE, NEGATIVE) and v.available]

    state = consensus.consensus_state
    if state in ("consensus_up", "lean_up"):
        text = f"{len(up)} trên {total} góc nhìn hướng giá đang nghiêng về tăng: {join_names(up)}."
        if flat:
            text += f" {join_names(flat)} chưa đưa ra hướng rõ ràng."
        return text
    if state in ("consensus_down", "lean_down"):
        text = f"{len(down)} trên {total} góc nhìn hướng giá đang nghiêng về giảm: {join_names(down)}."
        if flat:
            text += f" {join_names(flat)} chưa đưa ra hướng rõ ràng."
        return text
    if state == "conflict":
        return (
            f"Các góc nhìn hướng giá đang mâu thuẫn: {join_names(up)} nghiêng về tăng "
            f"trong khi {join_names(down)} nghiêng về giảm."
        )
    return (
        f"Cả {total} góc nhìn hướng giá đều nằm trong vùng trung tính, "
        "chưa góc nhìn nào đủ mạnh để chọn hướng."
    )


def _context_sentence(consensus: "SymbolConsensus") -> str:
    views = [v for v in consensus.views_by_role(CONTEXT) if v.available]
    if not views:
        return ""
    parts = [f"{v.name} cho thấy {v.reading.lower()}" for v in views]
    return "Về bối cảnh, " + join_names(parts) + "."


def _risk_sentence(consensus: "SymbolConsensus") -> str:
    views = [v for v in consensus.views_by_role(RISK) if v.available]
    if not views:
        return ""
    warnings = [v for v in views if v.perspective.is_unfavorable(v.stance)]
    if warnings:
        return "Về rủi ro, " + join_names(f"{v.name} cho thấy {v.reading.lower()}" for v in warnings) + "."
    return "Về rủi ro, chưa góc nhìn nào trong ba góc nhìn rủi ro phát tín hiệu cảnh báo."


def _conflict_sentences(consensus: "SymbolConsensus") -> list[str]:
    # Câu mở đầu đã liệt kê hai phía của mâu thuẫn hướng giá, không lặp lại nữa.
    seen: set[str] = {"directional"} if consensus.consensus_state == "conflict" else set()
    sentences: list[str] = []
    for note in consensus.conflicts:
        if note.kind in seen:
            continue
        seen.add(note.kind)
        sentences.append(note.message + ".")
        if len(sentences) >= MAX_CONFLICT_SENTENCES:
            break
    return sentences


def _overlap_sentence(consensus: "SymbolConsensus") -> str:
    overlap = consensus.overlap
    if not overlap.has_data:
        return ""

    covered = overlap.views_covered
    groups = overlap.independent_groups
    base = (
        f"{covered} góc nhìn có dữ liệu hiện gom thành {groups} nhóm thông tin "
        f"ở ngưỡng tương quan tuyệt đối {format_number(overlap.threshold)}."
    )

    shared = overlap.shared_clusters
    if not shared:
        return base + " Các góc nhìn đang phần lớn độc lập với nhau."

    if not overlap.pairs.empty:
        top = overlap.pairs.iloc[0]
        value = float(top["correlation"])
        direction = (
            "khi hai góc nhìn này cùng chiều"
            if value > 0
            else "khi hai góc nhìn này ngược chiều nhau"
        )
        base += (
            f" {top['model_a']} và {top['model_b']} đang chia sẻ nhiều thông tin nhất "
            f"(tương quan {format_number(value)}), "
            f"nên {direction} thì đó gần như là một xác nhận, không phải hai."
        )
    base += " Không góc nhìn nào bị loại bỏ vì tương quan cao."
    return base


def build_narrative(consensus: "SymbolConsensus") -> str:
    """Sinh đoạn Market Narrative cho một mã."""
    if not consensus.views:
        return "Không có dữ liệu cho mã này."

    sentences: list[str] = [_directional_sentence(consensus)]
    sentences.extend(_conflict_sentences(consensus))

    for sentence in (_context_sentence(consensus), _risk_sentence(consensus), _overlap_sentence(consensus)):
        if sentence:
            sentences.append(sentence)

    sentences.append(
        "Đây là mô tả cấu trúc đồng thuận giữa 9 góc nhìn, không phải điểm tổng hợp "
        "và không phải khuyến nghị đầu tư."
    )
    return " ".join(sentences)
