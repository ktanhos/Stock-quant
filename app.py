import html

import pandas as pd
import streamlit as st

from stock_quant.analysis import latest_analysis, run_signal_pipeline
from stock_quant.consensus import (
    CONTEXT,
    DIRECTIONAL,
    RISK,
    ROLE_LABELS,
    PERSPECTIVES_BY_KEY,
    consensus_overview,
    consensus_report,
    stance_tone,
    views_table,
)
from stock_quant.data import VnstockClient, validate_price_frame
from stock_quant.impact import (
    DEFAULT_WINDOW,
    IMPACT_HORIZONS,
    horizon_label,
    impact_highlights,
    impact_overview,
    impact_table,
    quintile_chart_frame,
    quintile_display,
    rolling_chart_frame,
    score_impact,
    stability_table,
)

st.set_page_config(page_title="Stock Quant · Consensus", layout="wide")

PANEL_LABEL = "Tất cả mã"
MIN_HISTORY = 130

STYLE = """
<style>
.sq-badge {
    display: inline-block;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}
.sq-chip {
    display: inline-block;
    padding: 0.08rem 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
}
.sq-card {
    border: 1px solid rgba(128, 128, 128, 0.28);
    border-radius: 10px;
    padding: 0.6rem 0.75rem;
    margin-bottom: 0.5rem;
}
.sq-card-title {
    font-weight: 700;
    font-size: 0.92rem;
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
}
.sq-card-score { font-variant-numeric: tabular-nums; opacity: 0.75; }
.sq-card-note { font-size: 0.78rem; opacity: 0.65; margin-top: 0.3rem; }
.sq-role-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.4rem; }
.sq-section-note { font-size: 0.82rem; opacity: 0.7; margin-bottom: 0.6rem; }
.sq-up   { background: rgba(22, 163, 74, 0.18);  color: #16a34a; }
.sq-down { background: rgba(220, 38, 38, 0.18);  color: #dc2626; }
.sq-warn { background: rgba(217, 119, 6, 0.18);  color: #d97706; }
.sq-calm { background: rgba(22, 163, 74, 0.14);  color: #16a34a; }
.sq-info { background: rgba(37, 99, 235, 0.16);  color: #2563eb; }
.sq-flat { background: rgba(128, 128, 128, 0.18); color: #6b7280; }
.sq-na   { background: rgba(128, 128, 128, 0.10); color: #9ca3af; }
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)

STATE_TONE = {
    "consensus_up": "up",
    "lean_up": "up",
    "consensus_down": "down",
    "lean_down": "down",
    "conflict": "warn",
    "neutral": "flat",
    "insufficient": "na",
}


def chip(text: str, tone: str) -> str:
    return f'<span class="sq-chip sq-{tone}">{html.escape(str(text))}</span>'


def badge(text: str, tone: str) -> str:
    return f'<span class="sq-badge sq-{tone}">{html.escape(str(text))}</span>'


def render_view_card(view) -> str:
    tone = stance_tone(view.perspective, view.stance)
    score = "—" if view.score is None else f"{view.score:+.0f}".replace("-", "−")
    cluster = f"Nhóm thông tin {view.cluster}" if view.cluster else "Nhóm thông tin —"
    return (
        '<div class="sq-card">'
        f'<div class="sq-card-title"><span>{html.escape(view.name)}</span>'
        f'<span class="sq-card-score">{score}</span></div>'
        f'<div style="margin-top:0.35rem">{chip(view.reading, tone)}</div>'
        f'<div class="sq-card-note">{html.escape(view.family)} · {html.escape(view.strength)} · '
        f'{html.escape(cluster)}</div>'
        "</div>"
    )


def render_symbol_header(report) -> None:
    date_text = report.date.date().isoformat() if report.date is not None else "—"
    counts = report.directional_counts

    header_left, header_right = st.columns([2, 3])
    with header_left:
        st.markdown(
            f"### {report.symbol} &nbsp; "
            f"{badge(report.consensus_label, STATE_TONE[report.consensus_state])}",
            unsafe_allow_html=True,
        )
        st.caption(f"Phiên gần nhất: {date_text}")
    with header_right:
        cols = st.columns(4)
        cols[0].metric("Hướng tăng", counts["up"])
        cols[1].metric("Hướng giảm", counts["down"])
        cols[2].metric("Trung tính", counts["neutral"])
        cols[3].metric(
            "Nhóm thông tin",
            f"{report.overlap.independent_groups}/{report.overlap.views_covered}"
            if report.overlap.has_data
            else "—",
            help="Số nhóm thông tin độc lập trên số góc nhìn đo được tương quan",
        )


# ----------------------------------------------------------------------------- 1. Current Signal


def render_current_signal(report) -> None:
    render_symbol_header(report)

    st.markdown("#### Chín góc nhìn độc lập")
    role_columns = st.columns(3)
    for column, role in zip(role_columns, (DIRECTIONAL, CONTEXT, RISK)):
        with column:
            st.markdown(
                f'<div class="sq-role-title">{ROLE_LABELS[role]}</div>', unsafe_allow_html=True
            )
            cards = "".join(render_view_card(view) for view in report.views_by_role(role))
            st.markdown(cards, unsafe_allow_html=True)

    for note in report.notes:
        st.caption(note)

    with st.expander(f"Số liệu gốc của 9 mô hình · {report.symbol}"):
        st.dataframe(views_table(report), width="stretch", hide_index=True)


# -------------------------------------------------------------------------------- 2. Score Impact


def render_impact_charts(impact, horizon: int, scope_key: str) -> None:
    names = {key: PERSPECTIVES_BY_KEY[key].name for key in impact.score_keys}
    if not names:
        st.info("Chưa có Score nào đủ dữ liệu để vẽ biểu đồ.")
        return

    score_key = st.selectbox(
        "Chọn một Score để xem chi tiết",
        options=list(names),
        format_func=lambda key: names[key],
        key=f"impact_score_{scope_key}",
    )

    left, right = st.columns(2)

    with left:
        st.markdown("**Score → Future Return**")
        st.caption(
            "Score được chia thành 5 nhóm bằng nhau, cột là Future Return trung bình (%) "
            "của từng nhóm."
        )
        chart = quintile_chart_frame(impact.quintiles, score_key)
        if chart.empty:
            st.info("Chưa đủ quan sát để chia nhóm quintile cho Score này.")
        else:
            st.bar_chart(chart, stack=False, height=280)

    with right:
        st.markdown("**IC theo thời gian**")
        st.caption(
            f"IC tính lại trên cửa sổ trượt {impact.window} phiên. "
            "Đường ổn định quanh một phía của trục 0 nghĩa là tác động giữ được dấu."
        )
        rolling = rolling_chart_frame(impact.rolling, score_key)
        if rolling.empty:
            st.info("Chưa đủ lịch sử để trượt cửa sổ IC cho Score này.")
        else:
            st.line_chart(rolling, height=280)

    table = quintile_display(impact, score_key, horizon)
    if table.empty:
        st.caption(
            f"Chưa có bảng quintile cho {names[score_key]} tại horizon {horizon_label(horizon)}."
        )
    else:
        st.markdown(
            f"**Quintile analysis · {names[score_key]} · {horizon_label(horizon)}**"
        )
        st.dataframe(table, width="stretch", hide_index=True)


def render_score_impact(impact, scope_key: str) -> None:
    st.markdown(
        '<div class="sq-section-note">'
        "Mỗi Score được đo riêng lẻ với Future Return 5D, 20D và 60D. "
        "Không Score nào được cộng với Score khác và không có trọng số nào được sinh ra."
        "</div>",
        unsafe_allow_html=True,
    )

    if not impact.has_data:
        st.warning(
            "Chưa đủ lịch sử để đo tác động của Score lên Future Return. "
            "Hãy mở rộng khoảng thời gian phân tích."
        )
        for note in impact.notes:
            st.caption(note)
        return

    st.info("\n".join(f"- {line}" for line in impact_highlights(impact)))

    st.markdown("#### Information Coefficient theo từng Score và từng horizon")
    st.caption(
        "Tương quan hạng Spearman giữa Score tại phiên t và Future Return sau đó. "
        f"Số quan sát: {impact.observations} dòng Score."
    )
    st.dataframe(impact.ic_matrix().round(3), width="stretch")

    horizon = st.radio(
        "Horizon",
        options=list(impact.horizons),
        format_func=horizon_label,
        horizontal=True,
        index=1 if len(impact.horizons) > 1 else 0,
        key=f"impact_horizon_{scope_key}",
    )

    detail = impact_table(impact, horizon)
    if not detail.empty:
        st.markdown(f"#### Chi tiết tại horizon {horizon_label(horizon)}")
        st.dataframe(detail, width="stretch", hide_index=True)

    st.markdown("#### Biểu đồ")
    render_impact_charts(impact, horizon, scope_key)

    with st.expander(f"Tính ổn định của IC theo thời gian · {horizon_label(horizon)}"):
        st.caption(
            "IC được tính lại trên từng cửa sổ trượt. Giữ dấu là tỉ lệ cửa sổ nghiêng về "
            "cùng một phía, IC / Độ lệch là tỉ số giữa IC trung bình và độ phân tán của nó."
        )
        stability = stability_table(impact, horizon)
        if stability.empty:
            st.write("Chưa đủ cửa sổ để đánh giá tính ổn định.")
        else:
            st.dataframe(stability, width="stretch", hide_index=True)

    with st.expander("Toàn bộ bảng quintile"):
        if impact.quintile_spread.empty:
            st.write("Chưa đủ quan sát để chia nhóm quintile.")
        else:
            summary = impact.quintile_spread.copy()
            display = pd.DataFrame(
                {
                    "Góc nhìn": summary["score_name"],
                    "Horizon": summary["horizon_label"],
                    "Q1 (%)": (summary["low_return"] * 100).round(2),
                    "Q5 (%)": (summary["high_return"] * 100).round(2),
                    "Q5 − Q1 (%)": (summary["spread"] * 100).round(2),
                    "Đơn điệu": summary["monotonicity"].round(2),
                    "Số quan sát": summary["observations"],
                }
            )
            st.dataframe(display, width="stretch", hide_index=True)

    for note in impact.notes:
        st.caption(note)


# --------------------------------------------------------------------------------- 3. Correlation


def render_correlation(report) -> None:
    overlap = report.overlap
    st.markdown(
        '<div class="sq-section-note">'
        "Correlation chỉ dùng để nhận biết các góc nhìn đang mang thông tin giống nhau. "
        "Không mô hình nào bị loại bỏ vì tương quan cao."
        "</div>",
        unsafe_allow_html=True,
    )

    if not overlap.has_data:
        st.warning("Chưa đủ quan sát để tính tương quan giữa các Score.")
        return

    st.caption(
        f"Ngưỡng |correlation| = {overlap.threshold:.2f} · "
        f"{overlap.views_covered} góc nhìn gom thành {overlap.independent_groups} nhóm thông tin."
    )

    st.markdown("**Nhóm thông tin**")
    for index, cluster in enumerate(overlap.clusters, start=1):
        names = ", ".join(PERSPECTIVES_BY_KEY[key].name for key in cluster)
        tag = "thông tin chung" if len(cluster) > 1 else "độc lập"
        st.markdown(f"- **Nhóm {index}** ({tag}): {names}")

    if not overlap.pairs.empty:
        st.markdown("**Các cặp vượt ngưỡng**")
        st.dataframe(
            overlap.pairs.drop(columns=["abs_correlation"])
            .rename(
                columns={
                    "model_a": "Góc nhìn A",
                    "model_b": "Góc nhìn B",
                    "correlation": "Tương quan",
                }
            )
            .round({"Tương quan": 2}),
            width="stretch",
            hide_index=True,
        )

    st.markdown("**Ma trận tương quan**")
    display = overlap.correlation.rename(
        index=lambda k: PERSPECTIVES_BY_KEY[k].name if k in PERSPECTIVES_BY_KEY else k,
        columns=lambda k: PERSPECTIVES_BY_KEY[k].name if k in PERSPECTIVES_BY_KEY else k,
    )
    st.dataframe(display.style.format("{:.2f}"), width="stretch")


# ------------------------------------------------------------------------------------ 4. Consensus


def render_consensus(report) -> None:
    st.markdown(
        '<div class="sq-section-note">'
        "Chín mô hình được đọc như chín góc nhìn độc lập. Các con số dưới đây là số lượng "
        "góc nhìn trong từng nhóm, không phải điểm tổng hợp."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("#### Market Narrative")
    st.info(report.narrative)

    left, middle, right = st.columns(3)

    with left:
        st.markdown("**Nhóm đồng thuận**")
        if report.agreement_groups:
            for group in report.agreement_groups:
                st.markdown(f"- **{group.label}** ({group.size}): " + ", ".join(group.names))
        else:
            st.markdown("- Chưa có nhóm nào từ hai góc nhìn trở lên nói cùng một điều")

    with middle:
        st.markdown("**Mâu thuẫn**")
        if report.conflicts:
            for note in report.conflicts:
                st.markdown(f"- {note.message}")
        else:
            st.markdown("- Không phát hiện mâu thuẫn giữa các góc nhìn")

    with right:
        st.markdown("**Trung tính**")
        if report.neutral_views:
            for view in report.neutral_views:
                st.markdown(f"- {view.name}: {view.reading.lower()}")
        else:
            st.markdown("- Không có góc nhìn nào nằm trong vùng trung tính")


# ------------------------------------------------------------------------------------------ Layout


@st.cache_data(show_spinner=False)
def build_impacts(result: pd.DataFrame, symbols: tuple[str, ...], window: int) -> dict:
    impacts = {symbol: score_impact(result, symbol=symbol, window=window) for symbol in symbols}
    if len(symbols) > 1:
        impacts[PANEL_LABEL] = score_impact(result, window=window)
    return impacts


st.title("Stock Quant")
st.caption(
    "Chín mô hình độc lập, đọc theo bốn tầng: Current Signal, Score Impact, Correlation "
    "và Consensus. Không có Composite Score và không có trọng số."
)

with st.sidebar:
    st.header("Dữ liệu")
    data_mode = st.radio("Nguồn dữ liệu", options=["API miễn phí", "API đã đăng ký"])
    if data_mode == "API miễn phí":
        st.caption("Thư viện vnstock theo kiến trúc Unified UI.")
    else:
        st.caption(
            "Thư viện vnstock_data theo cùng kiến trúc Unified UI. "
            "Thông tin xác thực do thư viện đã cài đặt quản lý."
        )

    symbols_text = st.text_input(
        "Mã cổ phiếu",
        value="VIC",
        help="Một hoặc nhiều mã, cách nhau bởi dấu cách hoặc dấu phẩy",
    )
    start = st.date_input("Ngày bắt đầu", value=None)
    end = st.date_input("Ngày kết thúc", value=None)

    st.header("Tham số phân tích")
    overlap_threshold = st.slider(
        "Ngưỡng thông tin chung |correlation|",
        min_value=0.50,
        max_value=0.95,
        value=0.70,
        step=0.05,
    )
    ic_window = st.slider(
        "Cửa sổ IC theo thời gian (phiên)",
        min_value=60,
        max_value=250,
        value=DEFAULT_WINDOW,
        step=10,
        help="Cửa sổ tự co lại khi lịch sử của mã ngắn hơn hai lần giá trị này",
    )
    run = st.button("Phân tích", type="primary", width="stretch")

if run:
    symbols = [
        symbol.strip().upper()
        for symbol in symbols_text.replace(",", " ").split()
        if symbol.strip()
    ]

    if not symbols:
        st.error("Chưa có mã cổ phiếu")
        st.stop()

    if start is None or end is None:
        st.error("Cần chọn ngày bắt đầu và ngày kết thúc")
        st.stop()

    mode = "registered" if data_mode == "API đã đăng ký" else "free"

    try:
        with st.spinner("Đang tải dữ liệu..."):
            client = VnstockClient(mode=mode)
            prices = client.fetch_price_history(symbols, str(start), str(end))

        validation = validate_price_frame(prices)
        if not validation.valid:
            st.error("Dữ liệu không hợp lệ: " + "; ".join(validation.errors))
            st.stop()

        if prices.empty:
            st.warning("Không có dữ liệu trả về cho mã và khoảng thời gian đã chọn")
            st.stop()

        with st.spinner("Đang chạy 9 mô hình..."):
            result = run_signal_pipeline(prices)

    except ImportError as exc:
        if mode == "registered":
            st.error(
                "Không thể sử dụng nguồn dữ liệu đã đăng ký vì môi trường Streamlit "
                "chưa có thư viện vnstock_data. Hãy cài vnstock_data theo trình cài "
                "đặt chính thức của Vnstock trong đúng môi trường Python đang chạy Streamlit."
            )
            st.code(str(exc))
        else:
            st.error(f"Không thể tải dữ liệu: {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"Không thể tải hoặc phân tích dữ liệu: {exc}")
        st.stop()

    st.session_state["result"] = result
    st.session_state["symbols"] = symbols
    st.session_state["counts"] = prices.groupby("symbol").size().rename("Số phiên")

if "result" not in st.session_state:
    st.info(
        "Chọn nguồn dữ liệu, nhập một hoặc nhiều mã rồi bấm Phân tích. "
        "Mỗi mô hình được đọc như một góc nhìn riêng về cổ phiếu."
    )
    st.stop()

result: pd.DataFrame = st.session_state["result"]
symbols: list[str] = st.session_state["symbols"]
counts: pd.Series = st.session_state["counts"]

reports = consensus_report(result, symbols, overlap_threshold=overlap_threshold)

if not reports:
    st.warning("Không có mã nào đủ dữ liệu để phân tích đồng thuận")
    st.stop()

insufficient = counts[counts < MIN_HISTORY]
if not insufficient.empty:
    detail = ", ".join(f"{symbol}: {count} phiên" for symbol, count in insufficient.items())
    st.warning("Một số mã chưa đủ lịch sử cho toàn bộ mô hình: " + detail)

report_symbols = tuple(report.symbol for report in reports)
with st.spinner("Đang đo tác động của từng Score..."):
    impacts = build_impacts(result, report_symbols, ic_window)

signal_tab, impact_tab, correlation_tab, consensus_tab = st.tabs(
    ["Current Signal", "Score Impact", "Correlation", "Consensus"]
)

with signal_tab:
    st.subheader("Current Signal")
    st.caption("Trạng thái của 9 góc nhìn tại phiên gần nhất.")

    if len(reports) > 1:
        st.markdown("**Tổng quan đồng thuận**")
        st.dataframe(consensus_overview(reports), width="stretch", hide_index=True)

    for tab, report in zip(st.tabs(list(report_symbols)), reports):
        with tab:
            render_current_signal(report)

    with st.expander("Bảng Score gốc tại phiên gần nhất"):
        st.caption(
            "Future Return tại phiên gần nhất không có giá trị vì chưa tồn tại dữ liệu tương lai."
        )
        st.dataframe(latest_analysis(result, symbols), width="stretch", hide_index=True)

with impact_tab:
    st.subheader("Score Impact")
    st.caption(
        "Tác động của từng Score lên Future Return "
        + ", ".join(horizon_label(h) for h in IMPACT_HORIZONS)
        + "."
    )

    scopes = list(report_symbols) + ([PANEL_LABEL] if len(reports) > 1 else [])

    if len(reports) > 1:
        st.markdown("**Tổng quan Score Impact**")
        st.caption("Score có |IC| lớn nhất ở từng horizon. Đây là kết quả đo, không phải trọng số.")
        st.dataframe(
            impact_overview([impacts[scope] for scope in scopes]),
            width="stretch",
            hide_index=True,
        )

    for tab, scope in zip(st.tabs(scopes), scopes):
        with tab:
            render_score_impact(impacts[scope], scope_key=scope)

with correlation_tab:
    st.subheader("Correlation")
    st.caption("Ma trận tương quan giữa 9 Score và các nhóm thông tin chung.")
    for tab, report in zip(st.tabs(list(report_symbols)), reports):
        with tab:
            render_correlation(report)

with consensus_tab:
    st.subheader("Consensus")
    st.caption("Đồng thuận, mâu thuẫn và trung tính giữa 9 góc nhìn.")
    for tab, report in zip(st.tabs(list(report_symbols)), reports):
        with tab:
            render_symbol_header(report)
            render_consensus(report)
            for note in report.notes:
                st.caption(note)
