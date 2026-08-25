"""Registry mô tả 9 mô hình hiện tại như 9 góc nhìn độc lập.

Module này không tạo ra Score mới và không đổi công thức của bất kỳ mô hình nào.
Nó chỉ khai báo ý nghĩa của từng Score để tầng Consensus có thể đọc hiểu chúng.
"""

from __future__ import annotations

from dataclasses import dataclass

DIRECTIONAL = "directional"
CONTEXT = "context"
RISK = "risk"
CONFIRMATION = "confirmation"
RISK_CONTEXT = "risk_context"
PROBABILISTIC = "probabilistic"

ROLE_LABELS = {
    DIRECTIONAL: "Hướng giá",
    CONTEXT: "Bối cảnh thị trường",
    RISK: "Rủi ro",
    CONFIRMATION: "Xác nhận",
    RISK_CONTEXT: "Bối cảnh rủi ro",
    PROBABILISTIC: "Xác suất",
}

ROLE_ORDER = (DIRECTIONAL, CONFIRMATION, RISK_CONTEXT, PROBABILISTIC)

POSITIVE = "positive"
NEUTRAL = "neutral"
NEGATIVE = "negative"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Perspective:
    """Một góc nhìn độc lập về cổ phiếu, gắn với đúng một Score đang có."""

    key: str
    name: str
    family: str
    role: str
    positive_reading: str
    negative_reading: str
    neutral_reading: str
    upper: float = 25.0
    lower: float = -25.0
    favorable_sign: int = 1
    question: str = ""

    def stance(self, score: float | None) -> str:
        if score is None:
            return UNAVAILABLE
        try:
            value = float(score)
        except (TypeError, ValueError):
            return UNAVAILABLE
        if value != value:  # NaN
            return UNAVAILABLE
        if value > self.upper:
            return POSITIVE
        if value < self.lower:
            return NEGATIVE
        return NEUTRAL

    def reading(self, stance: str) -> str:
        if stance == POSITIVE:
            return self.positive_reading
        if stance == NEGATIVE:
            return self.negative_reading
        if stance == NEUTRAL:
            return self.neutral_reading
        return "Chưa đủ lịch sử"

    def is_favorable(self, stance: str) -> bool:
        if stance == POSITIVE:
            return self.favorable_sign > 0
        if stance == NEGATIVE:
            return self.favorable_sign < 0
        return False

    def is_unfavorable(self, stance: str) -> bool:
        if stance == POSITIVE:
            return self.favorable_sign < 0
        if stance == NEGATIVE:
            return self.favorable_sign > 0
        return False


PERSPECTIVES: tuple[Perspective, ...] = (
    Perspective(
        key="tsm_score",
        name="Time Series Momentum",
        family="Momentum",
        role=DIRECTIONAL,
        positive_reading="Đà tăng",
        negative_reading="Đà giảm",
        neutral_reading="Đà đi ngang",
        question="Giá 20 và 60 phiên đang đi theo hướng nào và có tăng tốc không?",
    ),
    Perspective(
        key="vol_score",
        name="Vol Adjusted Edge",
        family="Momentum trên đơn vị biến động",
        role=DIRECTIONAL,
        positive_reading="Đà tăng lớn hơn mức biến động",
        negative_reading="Đà giảm lớn hơn mức biến động",
        neutral_reading="Đà chưa vượt mức biến động",
        question="Sau khi chia cho biến động, đà giá còn lại bao nhiêu?",
    ),
    Perspective(
        key="mr_score",
        name="Mean Reversion",
        family="Mean Reversion",
        role=DIRECTIONAL,
        positive_reading="Giá chiết khấu dưới trung bình 20 phiên",
        negative_reading="Giá căng trên trung bình 20 phiên",
        neutral_reading="Giá quanh trung bình 20 phiên",
        question="Giá đang lệch bao xa khỏi trung bình ngắn hạn của chính nó?",
    ),
    Perspective(
        key="mc_score",
        name="Monte Carlo",
        family="Monte Carlo",
        role=PROBABILISTIC,
        positive_reading="Xác suất mô phỏng nghiêng về tăng",
        negative_reading="Xác suất mô phỏng nghiêng về giảm",
        neutral_reading="Xác suất mô phỏng hai chiều cân bằng",
        upper=15.0,
        lower=-15.0,
        question="Mô phỏng ngẫu nhiên 20 phiên tới cho xác suất tăng bao nhiêu?",
    ),
    Perspective(
        key="vrh_score",
        name="Trend Persistence",
        family="Trend Persistence",
        role=CONFIRMATION,
        positive_reading="Chuỗi giá có quán tính",
        negative_reading="Chuỗi giá hay đảo chiều",
        neutral_reading="Quán tính không rõ",
        question="Chuỗi lợi nhuận đang nối tiếp hay triệt tiêu lẫn nhau?",
    ),
    Perspective(
        key="exp_score",
        name="Range Expansion",
        family="Range Expansion",
        role=DIRECTIONAL,
        positive_reading="Biên độ mở rộng",
        negative_reading="Biên độ co hẹp",
        neutral_reading="Biên độ ổn định",
        question="Biên độ hiện tại rộng hay hẹp so với 60 phiên gần nhất?",
    ),
    Perspective(
        key="vsf_score",
        name="Volatility Context",
        family="Volatility",
        role=RISK_CONTEXT,
        positive_reading="Biến động cao hơn nền 60 phiên",
        negative_reading="Biến động thấp hơn nền 60 phiên",
        neutral_reading="Biến động quanh nền 60 phiên",
        favorable_sign=-1,
        question="Mức biến động hiện tại đang ở đâu so với nền của chính nó?",
    ),
    Perspective(
        key="tail_score",
        name="Tail Risk",
        family="Tail Risk",
        role=RISK_CONTEXT,
        positive_reading="Đuôi phải chiếm ưu thế",
        negative_reading="Đuôi trái chiếm ưu thế",
        neutral_reading="Hai đuôi cân bằng",
        upper=20.0,
        lower=-20.0,
        question="Các phiên cực đoan nghiêng về phía tăng hay phía giảm?",
    ),
    Perspective(
        key="man_score",
        name="Market Integrity",
        family="Market Integrity",
        role=RISK_CONTEXT,
        positive_reading="Giao dịch bình thường",
        negative_reading="Có dấu hiệu giao dịch bất thường",
        neutral_reading="Giao dịch hơi bất thường",
        upper=-10.0,
        lower=-35.0,
        question="Gap, biên độ trong phiên và khối lượng có bất thường không?",
    ),
)

PERSPECTIVES_BY_KEY = {p.key: p for p in PERSPECTIVES}

SCORE_KEYS = tuple(p.key for p in PERSPECTIVES)


TONE_UP = "up"
TONE_DOWN = "down"
TONE_WARN = "warn"
TONE_CALM = "calm"
TONE_INFO = "info"
TONE_FLAT = "flat"
TONE_NA = "na"


def stance_tone(perspective: Perspective, stance: str) -> str:
    """Sắc thái hiển thị của một trạng thái, dùng cho giao diện."""
    if stance == UNAVAILABLE:
        return TONE_NA
    if stance == NEUTRAL:
        return TONE_FLAT
    if perspective.role == DIRECTIONAL:
        return TONE_UP if stance == POSITIVE else TONE_DOWN
    if perspective.role == RISK_CONTEXT:
        return TONE_CALM if perspective.is_favorable(stance) else TONE_WARN
    if perspective.role == CONFIRMATION:
        return TONE_UP if perspective.is_favorable(stance) else TONE_DOWN
    if perspective.role == PROBABILISTIC:
        return TONE_UP if stance == POSITIVE else TONE_DOWN
    return TONE_INFO


def perspectives_for_role(role: str) -> tuple[Perspective, ...]:
    return tuple(p for p in PERSPECTIVES if p.role == role)


def strength_label(score: float | None) -> str:
    if score is None:
        return "—"
    try:
        value = abs(float(score))
    except (TypeError, ValueError):
        return "—"
    if value != value:
        return "—"
    if value >= 60.0:
        return "Mạnh"
    if value >= 25.0:
        return "Vừa"
    return "Nhẹ"
