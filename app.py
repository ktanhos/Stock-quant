import html

import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
from stock_quant.research.score_research import (
    create_horizon_heatmap,
    create_score_scatter,
    create_score_timeseries_chart,
    score_research_summary,
)

st.set_page_config(page_title="Stock Quant · Consensus", layout="wide", initial_sidebar_state="expanded")

PANEL_LABEL = "Tất cả mã"
MIN_HISTORY = 130

STYLE = """
<style>
:root {
    --color-up: #10b981;
    --color-down: #ef4444;
    --color-neutral: #6b7280;
    --color-info: #3b82f6;
    --color-warn: #f59e0b;
    --color-bg-light: #f9fafb;
    --color-border: rgba(128, 128, 128, 0.28);
}

.sq-badge {
    display: inline-block;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.sq-chip {
    display: inline-block;
    padding: 0.08rem 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    transition: all 0.2s ease;
}

.sq-chip:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.sq-card {
    border: 1px solid var(--color-border);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%);
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.sq-card:hover {
    border-color: rgba(128, 128, 128, 0.4);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
}

.sq-card-title {
    font-weight: 700;
    font-size: 0.95rem;
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    color: #1f2937;
}

.sq-card-score {
    font-variant-numeric: tabular-nums;
    opacity: 0.8;
    font-weight: 600;
    font-size: 0.9rem;
}

.sq-card-note {
    font-size: 0.78rem;
    opacity: 0.65;
    margin-top: 0.4rem;
    line-height: 1.4;
}

.sq-role-title {
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 0.6rem;
    color: #1f2937;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid rgba(128, 128, 128, 0.15);
}

.sq-section-note {
    font-size: 0.82rem;
    opacity: 0.7;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: rgba(59, 130, 246, 0.05);
    border-left: 3px solid var(--color-info);
    border-radius: 4px;
}

.sq-metric-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.95) 100%);
    border: 1px solid var(--color-border);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.sq-metric-card:hover {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    transform: translateY(-4px);
}

.sq-metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1f2937;
    font-variant-numeric: tabular-nums;
}

.sq-metric-label {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 0.4rem;
    font-weight: 500;
}

.sq-up   { background: rgba(16, 185, 129, 0.15);  color: var(--color-up); border-left: 3px solid var(--color-up); }
.sq-down { background: rgba(239, 68, 68, 0.15);   color: var(--color-down); border-left: 3px solid var(--color-down); }
.sq-warn { background: rgba(245, 158, 11, 0.15);  color: var(--color-warn); border-left: 3px solid var(--color-warn); }
.sq-calm { background: rgba(16, 185, 129, 0.12);  color: var(--color-up); }
.sq-info { background: rgba(59, 130, 246, 0.15);  color: var(--color-info); border-left: 3px solid var(--color-info); }
.sq-flat { background: rgba(128, 128, 128, 0.15); color: var(--color-neutral); }
.sq-na   { background: rgba(128, 128, 128, 0.08); color: #9ca3af; }

.sq-chart-container {
    background: rgba(255, 255, 255, 0.8);
    border: 1px solid var(--color-border);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.sq-divider {
    height: 1px;
    background: linear-gradient(to right, transparent, rgba(128, 128, 128, 0.2), transparent);
    margin: 1.5rem 0;
}

@media (prefers-color-scheme: dark) {
    .sq-card, .sq-metric-card, .sq-chart-container {
        background-color: rgba(31, 41, 55, 0.5);
    }
}
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


def create_correlation_heatmap(corr_matrix):
    """Create interactive correlation heatmap using Plotly."""
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='RdBu',
        zmid=0,
        zmin=-1,
        zmax=1,
        text=corr_matrix.values.round(2),
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation"),
        hovertemplate='%{y} → %{x}<br>Correlation: %{z:.3f}<extra></extra>'
    ))
    fig.update_layout(
        height=500,
        margin=dict(l=150, r=50, t=50, b=100),
        font=dict(size=11),
        hovermode='closest',
    )
    return fig


def create_price_chart(prices_df, symbol: str):
    """Create interactive price chart with volume."""
    symbol_data = prices_df[prices_df['symbol'] == symbol].copy()
    symbol_data = symbol_data.sort_values('time')

    if symbol_data.empty:
        return None

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(
        go.Candlestick(
            x=symbol_data['time'],
            open=symbol_data['open'],
            high=symbol_data['high'],
            low=symbol_data['low'],
            close=symbol_data['close'],
            name=symbol,
            increasing_line_color='#10b981',
            decreasing_line_color='#ef4444',
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            x=symbol_data['time'],
            y=symbol_data['volume'],
            name='Volume',
            marker_color='rgba(59, 130, 246, 0.3)',
            showlegend=False,
        ),
        row=2, col=1
    )

    fig.update_yaxes(title_text="Giá", row=1, col=1)
    fig.update_yaxes(title_text="Khối lượng", row=2, col=1)
    fig.update_xaxes(title_text="Thời gian", row=2, col=1)

    fig.update_layout(
        height=400,
        hovermode='x unified',
        margin=dict(l=50, r=50, t=50, b=50),
    )
    return fig


def create_score_distribution(result_df, symbol: str):
    """Create score distribution visualization."""
    symbol_data = result_df[result_df.get('symbol') == symbol] if 'symbol' in result_df.columns else result_df

    if symbol_data.empty:
        return None

    score_cols = [col for col in symbol_data.columns if col.endswith('_score') and col != 'future_return']

    if not score_cols:
        return None

    fig = go.Figure()

    for col in score_cols[:6]:
        scores = symbol_data[col].dropna()
        fig.add_trace(go.Histogram(
            x=scores,
            name=col.replace('_score', '').replace('_', ' ').title(),
            opacity=0.7,
            nbinsx=15,
        ))

    fig.update_layout(
        height=350,
        barmode='overlay',
        title_text="Phân phối điểm Score",
        xaxis_title="Score Value",
        yaxis_title="Số lần",
        hovermode='x',
        margin=dict(l=50, r=50, t=50, b=50),
    )
    return fig


def create_ic_heatmap(ic_matrix_data):
    """Create interactive IC heatmap with color coding."""
    fig = go.Figure(data=go.Heatmap(
        z=ic_matrix_data.values,
        x=ic_matrix_data.columns,
        y=ic_matrix_data.index,
        colorscale='RdYlGn',
        zmid=0,
        text=ic_matrix_data.values.round(3),
        texttemplate='%{text:.3f}',
        textfont={"size": 10},
        colorbar=dict(title="IC"),
        hovertemplate='%{y} → %{x}<br>IC: %{z:.4f}<extra></extra>'
    ))
    fig.update_layout(
        height=400,
        margin=dict(l=150, r=50, t=50, b=100),
        font=dict(size=11),
        hovermode='closest',
        title_text="Information Coefficient Matrix",
    )
    return fig


def render_dashboard_overview(reports, impacts):
    """Render a comprehensive dashboard overview of key metrics."""
    st.markdown("## 📊 Dashboard Overview")

    col1, col2, col3, col4 = st.columns(4)

    total_views = sum(len(report.views) for report in reports)
    total_symbols = len(reports)

    avg_agreement = 0
    if reports:
        agreement_counts = [len(report.agreement_groups) for report in reports]
        avg_agreement = np.mean(agreement_counts) if agreement_counts else 0

    avg_ic = 0
    if reports:
        ic_values = []
        for report in reports:
            if report.symbol in impacts and impacts[report.symbol].has_data:
                ic_matrix = impacts[report.symbol].ic_matrix()
                ic_flat = ic_matrix.values.flatten()
                valid_ic = ic_flat[~np.isnan(ic_flat)]
                if len(valid_ic) > 0:
                    ic_values.append(valid_ic.mean())
        avg_ic = np.mean(ic_values) if ic_values else 0

    with col1:
        st.markdown(f'''
        <div class="sq-metric-card">
            <div class="sq-metric-value">{total_views}</div>
            <div class="sq-metric-label">Tổng góc nhìn</div>
        </div>
        ''', unsafe_allow_html=True)

    with col2:
        st.markdown(f'''
        <div class="sq-metric-card">
            <div class="sq-metric-value">{total_symbols}</div>
            <div class="sq-metric-label">Mã phân tích</div>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        st.markdown(f'''
        <div class="sq-metric-card">
            <div class="sq-metric-value">{avg_agreement:.1f}</div>
            <div class="sq-metric-label">Nhóm đồng thuận TB</div>
        </div>
        ''', unsafe_allow_html=True)

    with col4:
        st.markdown(f'''
        <div class="sq-metric-card">
            <div class="sq-metric-value">{avg_ic:.3f}</div>
            <div class="sq-metric-label">IC trung bình</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)


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

    st.markdown(
        f"## {report.symbol} &nbsp; "
        f"{badge(report.consensus_label, STATE_TONE[report.consensus_state])}",
        unsafe_allow_html=True,
    )
    st.caption(f"📅 Phiên gần nhất: {date_text}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f'''<div class="sq-metric-card">
            <div class="sq-metric-value" style="color: #10b981;">↑ {counts["up"]}</div>
            <div class="sq-metric-label">Hướng tăng</div>
            </div>''',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'''<div class="sq-metric-card">
            <div class="sq-metric-value" style="color: #ef4444;">↓ {counts["down"]}</div>
            <div class="sq-metric-label">Hướng giảm</div>
            </div>''',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f'''<div class="sq-metric-card">
            <div class="sq-metric-value" style="color: #6b7280;">=  {counts["neutral"]}</div>
            <div class="sq-metric-label">Trung tính</div>
            </div>''',
            unsafe_allow_html=True
        )

    with col4:
        group_text = (
            f"{report.overlap.independent_groups}/{report.overlap.views_covered}"
            if report.overlap.has_data
            else "—"
        )
        st.markdown(
            f'''<div class="sq-metric-card">
            <div class="sq-metric-value" style="color: #3b82f6;">{group_text}</div>
            <div class="sq-metric-label">Nhóm thông tin</div>
            </div>''',
            unsafe_allow_html=True
        )


# ----------------------------------------------------------------------------- 1. Current Signal


def render_current_signal(report) -> None:
    render_symbol_header(report)

    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    st.markdown("### 🎯 Chín góc nhìn độc lập")
    st.caption("Ba nhóm: Hướng tăng/giảm (Directional), Ngữ cảnh (Context), và Rủi ro (Risk)")

    role_columns = st.columns(3)
    for column, role in zip(role_columns, (DIRECTIONAL, CONTEXT, RISK)):
        with column:
            st.markdown(
                f'<div class="sq-role-title">🔹 {ROLE_LABELS[role]}</div>', unsafe_allow_html=True
            )
            cards = "".join(render_view_card(view) for view in report.views_by_role(role))
            st.markdown(cards, unsafe_allow_html=True)

    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    if report.notes:
        st.markdown("### 📌 Ghi chú")
        for note in report.notes:
            st.markdown(f"- {note}")

    with st.expander(f"📊 Bảng dữ liệu gốc của 9 mô hình", expanded=False):
        st.dataframe(views_table(report), width="stretch", hide_index=True)


# -------------------------------------------------------------------------------- 2. Score Impact


def render_impact_charts(impact, horizon: int, scope_key: str) -> None:
    names = {key: PERSPECTIVES_BY_KEY[key].name for key in impact.score_keys}
    if not names:
        st.info("💡 Chưa có Score nào đủ dữ liệu để vẽ biểu đồ.")
        return

    score_key = st.selectbox(
        "Chọn một Score để xem chi tiết",
        options=list(names),
        format_func=lambda key: names[key],
        key=f"impact_score_{scope_key}",
    )

    left, right = st.columns(2)

    with left:
        st.markdown("#### 📊 Score → Future Return")
        st.caption(
            "Score được chia thành 5 nhóm bằng nhau, cột là Future Return trung bình (%) "
            "của từng nhóm."
        )
        chart = quintile_chart_frame(impact.quintiles, score_key)
        if chart.empty:
            st.info("Chưa đủ quan sát để chia nhóm quintile cho Score này.")
        else:
            st.bar_chart(chart, stack=False, height=300)

    with right:
        st.markdown("#### 📈 IC theo thời gian")
        st.caption(
            f"IC tính lại trên cửa sổ trượt {impact.window} phiên. "
            "Đường ổn định quanh một phía của trục 0 nghĩa là tác động giữ được dấu."
        )
        rolling = rolling_chart_frame(impact.rolling, score_key)
        if rolling.empty:
            st.info("Chưa đủ lịch sử để trượt cửa sổ IC cho Score này.")
        else:
            st.line_chart(rolling, height=300)

    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    table = quintile_display(impact, score_key, horizon)
    if table.empty:
        st.caption(
            f"Chưa có bảng quintile cho {names[score_key]} tại horizon {horizon_label(horizon)}."
        )
    else:
        st.markdown(
            f"#### 📋 Quintile analysis · {names[score_key]} · {horizon_label(horizon)}"
        )
        st.dataframe(table, width="stretch", hide_index=True)


def render_score_impact(impact, scope_key: str) -> None:
    st.markdown(
        '<div class="sq-section-note">'
        "📊 Mỗi Score được đo riêng lẻ với Future Return 5D, 20D và 60D. "
        "Không Score nào được cộng với Score khác và không có trọng số nào được sinh ra."
        "</div>",
        unsafe_allow_html=True,
    )

    if not impact.has_data:
        st.warning(
            "⚠️ Chưa đủ lịch sử để đo tác động của Score lên Future Return. "
            "Hãy mở rộng khoảng thời gian phân tích."
        )
        for note in impact.notes:
            st.caption(note)
        return

    highlights = impact_highlights(impact)
    if highlights:
        st.success("🎯 **Những điểm nổi bật:**\n" + "\n".join(f"• {line}" for line in highlights))

    st.markdown("#### 📊 Information Coefficient theo từng Score và Horizon")
    st.caption(
        "Tương quan hạng Spearman giữa Score tại phiên t và Future Return sau đó. "
        f"Số quan sát: {impact.observations:,} dòng Score."
    )

    ic_matrix = impact.ic_matrix().round(3)

    tab_viz, tab_table = st.tabs(["📈 Biểu đồ", "📋 Bảng"])
    with tab_viz:
        ic_heatmap = create_ic_heatmap(ic_matrix)
        st.plotly_chart(ic_heatmap, use_container_width=True)
    with tab_table:
        st.dataframe(ic_matrix, width="stretch", use_container_width=True)

    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    horizon = st.radio(
        "Chọn Horizon",
        options=list(impact.horizons),
        format_func=horizon_label,
        horizontal=True,
        index=1 if len(impact.horizons) > 1 else 0,
        key=f"impact_horizon_{scope_key}",
    )

    detail = impact_table(impact, horizon)
    if not detail.empty:
        st.markdown(f"#### 📋 Chi tiết tại horizon {horizon_label(horizon)}")
        st.dataframe(detail, width="stretch", hide_index=True)
        st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    st.markdown("#### 📈 Biểu đồ chi tiết")
    render_impact_charts(impact, horizon, scope_key)

    col1, col2 = st.columns(2)

    with col1:
        with st.expander(f"📊 Tính ổn định của IC theo thời gian · {horizon_label(horizon)}", expanded=False):
            st.caption(
                "IC được tính lại trên từng cửa sổ trượt. Giữ dấu là tỉ lệ cửa sổ nghiêng về "
                "cùng một phía, IC / Độ lệch là tỉ số giữa IC trung bình và độ phân tán của nó."
            )
            stability = stability_table(impact, horizon)
            if stability.empty:
                st.write("Chưa đủ cửa sổ để đánh giá tính ổn định.")
            else:
                st.dataframe(stability, width="stretch", hide_index=True)

    with col2:
        with st.expander("📋 Toàn bộ bảng Quintile", expanded=False):
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

    if impact.notes:
        st.markdown("#### 📌 Ghi chú")
        for note in impact.notes:
            st.caption(f"• {note}")


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

    st.markdown(f"#### 📊 Phân tích Tương quan")
    st.caption(
        f"Ngưỡng |correlation| = {overlap.threshold:.2f} · "
        f"{overlap.views_covered} góc nhìn gom thành {overlap.independent_groups} nhóm thông tin."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Nhóm thông tin**")
        for index, cluster in enumerate(overlap.clusters, start=1):
            names = ", ".join(PERSPECTIVES_BY_KEY[key].name for key in cluster)
            tag = "thông tin chung" if len(cluster) > 1 else "độc lập"
            st.markdown(f"- **Nhóm {index}** ({tag}): {names}")

    with col2:
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
        else:
            st.markdown("**Các cặp vượt ngưỡng**")
            st.info("Không có cặp nào vượt ngưỡng tương quan.")

    st.markdown("**Ma trận tương quan (Heatmap)**")
    display = overlap.correlation.rename(
        index=lambda k: PERSPECTIVES_BY_KEY[k].name if k in PERSPECTIVES_BY_KEY else k,
        columns=lambda k: PERSPECTIVES_BY_KEY[k].name if k in PERSPECTIVES_BY_KEY else k,
    )

    heatmap = create_correlation_heatmap(display)
    st.plotly_chart(heatmap, use_container_width=True)

    with st.expander("Xem bảng tương quan chi tiết"):
        st.dataframe(display.style.format("{:.2f}"), width="stretch")


# ------------------------------------------------------------------------------------ 4. Consensus


def render_consensus(report) -> None:
    st.markdown(
        '<div class="sq-section-note">'
        "💡 Chín mô hình được đọc như chín góc nhìn độc lập. Các con số dưới đây là số lượng "
        "góc nhìn trong từng nhóm, không phải điểm tổng hợp."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("#### 📖 Market Narrative")
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.08) 100%);
                border-left: 4px solid #3b82f6; border-radius: 8px; padding: 1.25rem;
                margin-bottom: 1rem;">
        <p style="margin: 0; color: #1f2937; line-height: 1.6;">
            <span style="font-size: 1.1rem; margin-right: 0.5rem;">💬</span>
            {report.narrative}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### ✅ Nhóm đồng thuận")
        if report.agreement_groups:
            for group in report.agreement_groups:
                st.markdown(
                    f'<div class="sq-card"><strong>{group.label}</strong> '
                    f'<span style="opacity: 0.7;">({group.size})</span><br>'
                    f'<small>{", ".join(group.names)}</small></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="padding: 1rem; text-align: center; opacity: 0.6; color: #6b7280;">'
                '➖ Chưa có nhóm đồng thuận từ 2+ góc nhìn'
                '</div>',
                unsafe_allow_html=True
            )

    with col2:
        st.markdown("#### ⚠️ Mâu thuẫn")
        if report.conflicts:
            for note in report.conflicts:
                st.markdown(
                    f'<div class="sq-card sq-warn">{note.message}</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="padding: 1rem; text-align: center; opacity: 0.6; color: #6b7280;">'
                '✓ Không có mâu thuẫn giữa các góc nhìn'
                '</div>',
                unsafe_allow_html=True
            )

    with col3:
        st.markdown("#### 〰️ Trung tính")
        if report.neutral_views:
            for view in report.neutral_views:
                st.markdown(
                    f'<div class="sq-card sq-flat"><strong>{view.name}</strong><br>'
                    f'<small>{view.reading.lower()}</small></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="padding: 1rem; text-align: center; opacity: 0.6; color: #6b7280;">'
                '➖ Không có góc nhìn trung tính'
                '</div>',
                unsafe_allow_html=True
            )


# ------------------------------------------------------------------------------------------ Layout


@st.cache_data(show_spinner=False)
def build_impacts(result: pd.DataFrame, symbols: tuple[str, ...], window: int) -> dict:
    impacts = {symbol: score_impact(result, symbol=symbol, window=window) for symbol in symbols}
    if len(symbols) > 1:
        impacts[PANEL_LABEL] = score_impact(result, window=window)
    return impacts


st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%);
                border-radius: 12px; padding: 2rem 1.5rem; text-align: center; margin-bottom: 1rem;">
        <h1 style="margin: 0; color: #1f2937; font-size: 2.5rem;">📈 Stock Quant</h1>
        <p style="color: #6b7280; margin-top: 0.75rem; font-size: 1.1rem; line-height: 1.6;">
            <strong>Phân tích cổ phiếu với 9 mô hình độc lập</strong><br>
            <span style="font-size: 0.95rem;">Đánh giá tin cậy • Không Composite Score • Không trọng số</span>
        </p>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display: flex; justify-content: center; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-weight: 600; font-size: 1.1rem;">📊</span>
        <span style="color: #6b7280; font-weight: 500;">Current Signal</span>
    </div>
    <span style="color: #d1d5db; opacity: 0.5;">•</span>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-weight: 600; font-size: 1.1rem;">📈</span>
        <span style="color: #6b7280; font-weight: 500;">Score Impact</span>
    </div>
    <span style="color: #d1d5db; opacity: 0.5;">•</span>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-weight: 600; font-size: 1.1rem;">🔗</span>
        <span style="color: #6b7280; font-weight: 500;">Correlation</span>
    </div>
    <span style="color: #d1d5db; opacity: 0.5;">•</span>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-weight: 600; font-size: 1.1rem;">💡</span>
        <span style="color: #6b7280; font-weight: 500;">Consensus</span>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <style>
    .sidebar-section {
        padding: 1rem 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    }
    .sidebar-section:last-child {
        border-bottom: none;
    }
    .sidebar-title {
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        color: #1f2937;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">📊 Nguồn Dữ liệu</div>', unsafe_allow_html=True)
    data_mode = st.radio("Chọn API", options=["API miễn phí", "API đã đăng ký"], label_visibility="collapsed")
    if data_mode == "API miễn phí":
        st.caption("✓ Thư viện vnstock theo kiến trúc Unified UI.")
    else:
        st.caption(
            "✓ Thư viện vnstock_data theo cùng kiến trúc Unified UI. "
            "Thông tin xác thực do thư viện đã cài đặt quản lý."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">🔍 Tìm kiếm</div>', unsafe_allow_html=True)
    symbols_text = st.text_input(
        "Mã cổ phiếu",
        value="VIC",
        help="Một hoặc nhiều mã, cách nhau bởi dấu cách hoặc dấu phẩy",
        label_visibility="collapsed"
    )
    col_start, col_end = st.columns(2)
    with col_start:
        start = st.date_input("Từ ngày", value=None, label_visibility="collapsed")
    with col_end:
        end = st.date_input("Đến ngày", value=None, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">⚙️ Tham số phân tích</div>', unsafe_allow_html=True)
    st.caption("Ngưỡng tương quan và cửa sổ thời gian IC")

    overlap_threshold = st.slider(
        "Ngưỡng |correlation|",
        min_value=0.50,
        max_value=0.95,
        value=0.70,
        step=0.05,
        label_visibility="collapsed"
    )

    ic_window = st.slider(
        "Cửa sổ IC (phiên)",
        min_value=60,
        max_value=250,
        value=DEFAULT_WINDOW,
        step=10,
        help="Cửa sổ tự co lại khi lịch sử của mã ngắn hơn hai lần giá trị này",
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    run = st.button("🚀 Phân tích", type="primary", width="stretch")
    st.markdown('</div>', unsafe_allow_html=True)

if run:
    symbols = [
        symbol.strip().upper()
        for symbol in symbols_text.replace(",", " ").split()
        if symbol.strip()
    ]

    if not symbols:
        st.error("❌ Vui lòng nhập ít nhất một mã cổ phiếu")
        st.stop()

    if start is None or end is None:
        st.error("❌ Vui lòng chọn cả ngày bắt đầu và ngày kết thúc")
        st.stop()

    if start >= end:
        st.error("❌ Ngày bắt đầu phải trước ngày kết thúc")
        st.stop()

    mode = "registered" if data_mode == "API đã đăng ký" else "free"

    try:
        with st.spinner("⏳ Đang tải dữ liệu từ API..."):
            client = VnstockClient(mode=mode)
            prices = client.fetch_price_history(symbols, str(start), str(end))

        validation = validate_price_frame(prices)
        if not validation.valid:
            st.error("❌ Dữ liệu không hợp lệ:\n" + "\n".join(f"• {error}" for error in validation.errors))
            st.stop()

        if prices.empty:
            st.warning("⚠️ Không có dữ liệu trả về cho mã và khoảng thời gian đã chọn")
            st.stop()

        with st.spinner("⏳ Đang chạy 9 mô hình phân tích..."):
            result = run_signal_pipeline(prices)

        st.success(f"✅ Phân tích thành công! Xử lý {len(symbols)} mã cổ phiếu")

    except ImportError as exc:
        if mode == "registered":
            st.error(
                "❌ **Lỗi Library:** Không thể sử dụng API đã đăng ký\n\n"
                "Vui lòng cài đặt vnstock_data theo hướng dẫn chính thức."
            )
            with st.expander("📋 Chi tiết lỗi"):
                st.code(str(exc))
        else:
            st.error(f"❌ **Lỗi tải dữ liệu:** {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"❌ **Lỗi xử lý:** Không thể tải hoặc phân tích dữ liệu")
        with st.expander("📋 Chi tiết lỗi"):
            st.code(str(exc))
        st.stop()

    st.session_state["result"] = result
    st.session_state["symbols"] = symbols
    st.session_state["counts"] = prices.groupby("symbol").size().rename("Số phiên")

if "result" not in st.session_state:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(16, 185, 129, 0.08) 100%);
                border-radius: 12px; padding: 2rem; text-align: center; margin-top: 2rem;">
        <h3 style="color: #1f2937; margin-top: 0;">🚀 Bắt đầu phân tích</h3>
        <p style="color: #6b7280; margin-bottom: 0;">
            Sử dụng bảng điều khiển bên trái để chọn nguồn dữ liệu, nhập mã cổ phiếu và khoảng thời gian,<br>
            sau đó nhấn <strong>Phân tích</strong> để xem kết quả.
        </p>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 2rem;">
        <div style="background: rgba(16, 185, 129, 0.08); border-radius: 12px; padding: 1.5rem; border-left: 4px solid #10b981;">
            <h4 style="color: #1f2937; margin-top: 0;">📊 Cách hoạt động</h4>
            <ul style="color: #6b7280; line-height: 1.8; margin-bottom: 0;">
                <li>9 mô hình độc lập phân tích cổ phiếu</li>
                <li>Mỗi mô hình là 1 góc nhìn riêng</li>
                <li>Không có điểm tổng hợp hoặc trọng số</li>
            </ul>
        </div>
        <div style="background: rgba(59, 130, 246, 0.08); border-radius: 12px; padding: 1.5rem; border-left: 4px solid #3b82f6;">
            <h4 style="color: #1f2937; margin-top: 0;">📈 4 Tầng phân tích</h4>
            <ul style="color: #6b7280; line-height: 1.8; margin-bottom: 0;">
                <li><strong>Current Signal:</strong> Tín hiệu hiện tại</li>
                <li><strong>Score Impact:</strong> Tác động của điểm</li>
                <li><strong>Correlation:</strong> Tương quan</li>
                <li><strong>Consensus:</strong> Đồng thuận</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

result: pd.DataFrame = st.session_state["result"]
symbols: list[str] = st.session_state["symbols"]
counts: pd.Series = st.session_state["counts"]

reports = consensus_report(result, symbols, overlap_threshold=overlap_threshold)

if not reports:
    st.warning("⚠️ Không có mã nào đủ dữ liệu để phân tích đồng thuận")
    st.stop()

insufficient = counts[counts < MIN_HISTORY]
if not insufficient.empty:
    detail = ", ".join(f"{symbol}: {count} phiên" for symbol, count in insufficient.items())
    st.warning("⚠️ Một số mã chưa đủ lịch sử cho toàn bộ mô hình: " + detail)

report_symbols = tuple(report.symbol for report in reports)
with st.spinner("⏳ Đang đo tác động của từng Score..."):
    impacts = build_impacts(result, report_symbols, ic_window)

signal_tab, impact_tab, correlation_tab, consensus_tab, research_tab = st.tabs(
    ["📊 Current Signal", "📈 Score Impact", "🔗 Correlation", "💡 Consensus", "🔬 Research"]
)

with signal_tab:
    render_dashboard_overview(reports, impacts)

    st.markdown("## 📊 Current Signal")
    st.caption("🔍 Trạng thái của 9 góc nhìn tại phiên gần nhất.")
    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    if len(reports) > 1:
        st.markdown("#### 👁️ Tổng quan đồng thuận")
        overview_df = consensus_overview(reports)
        st.dataframe(overview_df, width="stretch", hide_index=True)
        st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    for tab, report in zip(st.tabs(list(report_symbols)), reports):
        with tab:
            render_current_signal(report)

    with st.expander("📋 Bảng Score gốc tại phiên gần nhất", expanded=False):
        st.caption(
            "💡 Future Return tại phiên gần nhất không có giá trị vì chưa tồn tại dữ liệu tương lai."
        )
        st.dataframe(latest_analysis(result, symbols), width="stretch", hide_index=True)

with impact_tab:
    st.markdown("## 📈 Score Impact")
    st.caption(
        "📊 Tác động của từng Score lên Future Return: "
        + ", ".join(horizon_label(h) for h in IMPACT_HORIZONS)
        + "."
    )
    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    scopes = list(report_symbols) + ([PANEL_LABEL] if len(reports) > 1 else [])

    if len(reports) > 1:
        st.markdown("#### 📊 Tổng quan Score Impact")
        st.caption("🎯 Score có |IC| lớn nhất ở từng horizon. Đây là kết quả đo, không phải trọng số.")
        st.dataframe(
            impact_overview([impacts[scope] for scope in scopes]),
            width="stretch",
            hide_index=True,
        )
        st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    for tab, scope in zip(st.tabs(scopes), scopes):
        with tab:
            render_score_impact(impacts[scope], scope_key=scope)

with correlation_tab:
    st.markdown("## 🔗 Correlation")
    st.caption("📊 Ma trận tương quan giữa 9 Score và các nhóm thông tin chung.")
    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    for tab, report in zip(st.tabs(list(report_symbols)), reports):
        with tab:
            render_correlation(report)

with consensus_tab:
    st.markdown("## 💡 Consensus")
    st.caption("🤝 Đồng thuận, mâu thuẫn và trung tính giữa 9 góc nhìn.")
    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    for tab, report in zip(st.tabs(list(report_symbols)), reports):
        with tab:
            render_symbol_header(report)
            st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)
            render_consensus(report)
            if report.notes:
                st.markdown('#### 📌 Ghi chú bổ sung')
                for note in report.notes:
                    st.caption(f"• {note}")

with research_tab:
    st.markdown("## 🔬 Research")
    st.caption("📊 Nghiên cứu mối quan hệ giữa Score và Future Return.")
    st.markdown('<div class="sq-divider"></div>', unsafe_allow_html=True)

    score_keys = [k for k in ["tsm_score", "vol_score", "mr_score", "exp_score", "vrh_score",
                             "vsf_score", "tail_score", "man_score", "mc_score"] if k in result.columns]

    if len(report_symbols) > 1:
        for tab, sym in zip(st.tabs(list(report_symbols)), report_symbols):
            with tab:
                sym_data = result[result["symbol"] == sym]

                st.subheader("📈 Score & Price Time Series")
                selected_score = st.selectbox("Chọn Score", score_keys, key=f"score_select_{sym}")
                fig_ts = create_score_timeseries_chart(sym_data, selected_score)
                st.plotly_chart(fig_ts, use_container_width=True)

                st.subheader("🎯 Score vs Future Return (Scatter)")
                col1, col2 = st.columns(2)
                with col1:
                    selected_horizon = st.selectbox("Horizon", [5, 20, 60], key=f"horizon_select_{sym}")
                with col2:
                    selected_score_scatter = st.selectbox("Score", score_keys, key=f"score_scatter_{sym}")

                fig_scatter, stats = create_score_scatter(sym_data, selected_score_scatter, horizon=selected_horizon)
                st.plotly_chart(fig_scatter, use_container_width=True)

                if not pd.isna(stats.get("correlation")):
                    st.caption(f"Correlation: {stats['correlation']:.3f} | p-value: {stats['p_value']:.4f}")

                st.subheader("🔥 Horizon Heatmap")
                fig_heatmap = create_horizon_heatmap(sym_data, score_keys=score_keys, horizons=(5, 10, 20, 60))
                st.plotly_chart(fig_heatmap, use_container_width=True)

                st.subheader("📋 Score-Return Summary")
                summary_table = score_research_summary(sym_data, score_keys=score_keys, horizons=(5, 20, 60))
                st.dataframe(summary_table, use_container_width=True, hide_index=True)
    else:
        sym_data = result

        st.subheader("📈 Score & Price Time Series")
        selected_score = st.selectbox("Chọn Score", score_keys)
        fig_ts = create_score_timeseries_chart(sym_data, selected_score)
        st.plotly_chart(fig_ts, use_container_width=True)

        st.subheader("🎯 Score vs Future Return (Scatter)")
        col1, col2 = st.columns(2)
        with col1:
            selected_horizon = st.selectbox("Horizon", [5, 20, 60])
        with col2:
            selected_score_scatter = st.selectbox("Score", score_keys)

        fig_scatter, stats = create_score_scatter(sym_data, selected_score_scatter, horizon=selected_horizon)
        st.plotly_chart(fig_scatter, use_container_width=True)

        if not pd.isna(stats.get("correlation")):
            st.caption(f"Correlation: {stats['correlation']:.3f} | p-value: {stats['p_value']:.4f}")

        st.subheader("🔥 Horizon Heatmap")
        fig_heatmap = create_horizon_heatmap(sym_data, score_keys=score_keys, horizons=(5, 10, 20, 60))
        st.plotly_chart(fig_heatmap, use_container_width=True)

        st.subheader("📋 Score-Return Summary")
        summary_table = score_research_summary(sym_data, score_keys=score_keys, horizons=(5, 20, 60))
        st.dataframe(summary_table, use_container_width=True, hide_index=True)
