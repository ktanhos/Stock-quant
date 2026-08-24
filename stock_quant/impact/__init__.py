"""Score Impact: đo tác động của từng Score lên Future Return.

Tầng này trả lời một câu hỏi duy nhất cho mỗi mô hình: khi Score của mô hình đó cao
hay thấp thì lợi nhuận 5, 20 và 60 phiên sau đó khác nhau thế nào. Bốn công cụ được
dùng là Information Coefficient, quintile analysis, độ ổn định của IC theo thời gian
và các biểu đồ đi kèm.

Tầng này **không** tạo Composite Score, **không** cộng hay trung bình 9 Score với
nhau, và **không** đề xuất trọng số. Nó cũng không đổi công thức của bất kỳ mô hình nào.
"""

from .horizons import (
    HORIZON_LABELS,
    IMPACT_HORIZONS,
    ensure_forward_returns,
    forward_return_column,
    horizon_label,
)
from .ic import (
    DEFAULT_MIN_OBS,
    ICStat,
    ic_direction,
    ic_matrix,
    ic_strength,
    panel_ic_table,
    score_keys,
    spearman_ic,
    symbol_ic_table,
)
from .quintiles import (
    DEFAULT_BUCKETS,
    assign_buckets,
    quintile_chart_frame,
    quintile_profile,
    quintile_summary,
    quintile_table,
)
from .report import (
    MEANINGFUL_IC,
    ScoreImpact,
    impact_highlights,
    impact_overview,
    impact_table,
    quintile_display,
    score_impact,
    stability_table,
)
from .stability import (
    DEFAULT_STEP,
    DEFAULT_WINDOW,
    effective_window,
    ic_stability,
    rolling_chart_frame,
    rolling_ic,
    rolling_ic_series,
    stability_label,
)

__all__ = [
    "IMPACT_HORIZONS",
    "HORIZON_LABELS",
    "horizon_label",
    "forward_return_column",
    "ensure_forward_returns",
    "ICStat",
    "DEFAULT_MIN_OBS",
    "spearman_ic",
    "score_keys",
    "symbol_ic_table",
    "panel_ic_table",
    "ic_matrix",
    "ic_strength",
    "ic_direction",
    "DEFAULT_BUCKETS",
    "assign_buckets",
    "quintile_table",
    "quintile_profile",
    "quintile_summary",
    "quintile_chart_frame",
    "DEFAULT_WINDOW",
    "DEFAULT_STEP",
    "effective_window",
    "rolling_ic_series",
    "rolling_ic",
    "ic_stability",
    "stability_label",
    "rolling_chart_frame",
    "MEANINGFUL_IC",
    "ScoreImpact",
    "score_impact",
    "impact_table",
    "stability_table",
    "quintile_display",
    "impact_highlights",
    "impact_overview",
]
