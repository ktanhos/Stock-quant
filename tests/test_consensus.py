import numpy as np
import pandas as pd
import pytest

from stock_quant.analysis import run_signal_pipeline
from stock_quant.consensus import (
    CONSENSUS_LABELS,
    DIRECTIONAL,
    NEGATIVE,
    PERSPECTIVES,
    POSITIVE,
    RISK,
    SCORE_KEYS,
    analyze_symbol,
    consensus_overview,
    consensus_report,
    information_clusters,
    overlap_pairs,
    views_table,
)
from stock_quant.consensus.perspectives import PERSPECTIVES_BY_KEY


def make_prices(symbols=("MSR", "FPT"), periods=200, drift=0.0015):
    dates = pd.date_range("2023-01-02", periods=periods, freq="B")
    rows = []
    for j, symbol in enumerate(symbols):
        base = 100 + 20 * j
        sign = 1 if j % 2 == 0 else -1
        for i, date in enumerate(dates):
            close = base * np.exp(sign * drift * i + 0.015 * np.sin(i / 7))
            rows.append(
                {
                    "symbol": symbol,
                    "date": date,
                    "open": close * 0.998,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 1_000_000 + i * 2_000,
                    "value": close * (1_000_000 + i * 2_000),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def pipeline_result():
    return run_signal_pipeline(make_prices(), monte_carlo_simulations=300, monte_carlo_stride=10)


def test_pipeline_produces_all_nine_scores(pipeline_result):
    for key in SCORE_KEYS:
        assert key in pipeline_result.columns, key
    assert pipeline_result["mc_score"].notna().any()


def test_pipeline_has_no_composite_score(pipeline_result):
    banned = {"composite", "composite_score", "total_score", "overall_score", "final_score"}
    assert banned.isdisjoint(set(pipeline_result.columns))


def test_registry_covers_nine_distinct_perspectives():
    assert len(PERSPECTIVES) == 9
    assert len({p.key for p in PERSPECTIVES}) == 9
    families = {p.family for p in PERSPECTIVES}
    for expected in ("Momentum", "Range Expansion", "Volatility", "Mean Reversion",
                     "Trend Persistence", "Tail Risk", "Monte Carlo", "Market Integrity"):
        assert expected in families
    roles = {p.role for p in PERSPECTIVES}
    assert roles == {"directional", "context", "risk"}


def test_report_covers_every_symbol_and_view(pipeline_result):
    reports = consensus_report(pipeline_result)
    assert [r.symbol for r in reports] == ["FPT", "MSR"]
    for report in reports:
        assert len(report.views) == 9
        assert report.consensus_state in CONSENSUS_LABELS
        assert report.narrative
        assert "khuyến nghị" in report.narrative


def test_single_symbol_is_supported(pipeline_result):
    reports = consensus_report(pipeline_result, symbols=["msr"])
    assert len(reports) == 1
    assert reports[0].symbol == "MSR"


def test_counts_match_view_stances(pipeline_result):
    for report in consensus_report(pipeline_result):
        directional = report.views_by_role(DIRECTIONAL)
        counts = report.directional_counts
        assert counts["up"] == sum(1 for v in directional if v.stance == POSITIVE)
        assert counts["down"] == sum(1 for v in directional if v.stance == NEGATIVE)
        assert sum(counts.values()) == len(directional)


def test_opposite_trends_give_opposite_states(pipeline_result):
    reports = {r.symbol: r for r in consensus_report(pipeline_result)}
    up_counts = reports["MSR"].directional_counts
    down_counts = reports["FPT"].directional_counts
    assert up_counts["up"] > up_counts["down"]
    assert down_counts["down"] > down_counts["up"]


def test_conflict_state_when_views_disagree():
    history = pd.DataFrame(
        {
            "symbol": ["AAA"] * 40,
            "date": pd.date_range("2024-01-01", periods=40, freq="B"),
            "tsm_score": np.linspace(40, 80, 40),
            "vol_score": np.linspace(30, 70, 40),
            "mr_score": np.linspace(-30, -70, 40),
            "mc_score": np.linspace(5, 10, 40),
            "vrh_score": np.linspace(-10, -60, 40),
            "exp_score": np.linspace(10, 60, 40),
            "vsf_score": np.linspace(10, 70, 40),
            "tail_score": np.linspace(-5, -40, 40),
            "man_score": np.linspace(-5, -50, 40),
        }
    )
    report = analyze_symbol(history, "AAA")
    assert report.consensus_state == "conflict"
    assert report.consensus_label == "Mâu thuẫn"
    kinds = {note.kind for note in report.conflicts}
    assert "directional" in kinds
    assert "persistence" in kinds
    assert "expansion_risk" in kinds
    assert "integrity" in kinds
    assert any(v.perspective.is_unfavorable(v.stance) for v in report.views_by_role(RISK))


def test_neutral_state_when_no_view_is_strong():
    history = pd.DataFrame(
        {
            "symbol": ["BBB"] * 30,
            "date": pd.date_range("2024-01-01", periods=30, freq="B"),
            "tsm_score": np.linspace(-5, 5, 30),
            "vol_score": np.linspace(-4, 4, 30),
            "mr_score": np.linspace(-3, 3, 30),
            "mc_score": np.linspace(-2, 2, 30),
            "vrh_score": np.linspace(-6, 6, 30),
            "exp_score": np.linspace(-5, 5, 30),
            "vsf_score": np.linspace(-4, 4, 30),
            "tail_score": np.linspace(-3, 3, 30),
            "man_score": np.linspace(-20, -20, 30),
        }
    )
    report = analyze_symbol(history, "BBB")
    assert report.consensus_state == "neutral"
    assert len(report.neutral_views) >= 8


def test_missing_scores_are_reported_not_dropped():
    history = pd.DataFrame(
        {
            "symbol": ["CCC"] * 30,
            "date": pd.date_range("2024-01-01", periods=30, freq="B"),
            "tsm_score": np.linspace(40, 60, 30),
            "mc_score": np.full(30, np.nan),
        }
    )
    report = analyze_symbol(history, "CCC")
    assert len(report.views) == 9
    assert report.view("mc_score").stance == "unavailable"
    assert report.view("mc_score").reading == "Chưa đủ lịch sử"
    assert any("Chưa đủ lịch sử cho" in note for note in report.notes)


def test_correlation_detects_shared_information_without_dropping_models(pipeline_result):
    report = consensus_report(pipeline_result, symbols=["MSR"])[0]
    overlap = report.overlap
    assert overlap.has_data
    assert overlap.views_covered == len(overlap.correlation.columns)
    assert overlap.independent_groups <= overlap.views_covered
    flattened = [key for cluster in overlap.clusters for key in cluster]
    assert sorted(flattened) == sorted(overlap.correlation.columns)
    assert len(report.views) == 9


def test_information_clusters_group_duplicate_signals():
    frame = pd.DataFrame(
        {
            "tsm_score": [1.0, 2.0, 3.0, 4.0, 5.0],
            "vol_score": [2.0, 4.0, 6.0, 8.0, 10.0],
            "mr_score": [5.0, 1.0, 4.0, 2.0, 3.0],
        }
    )
    corr = frame.corr()
    clusters = information_clusters(corr, threshold=0.7)
    grouped = {frozenset(c) for c in clusters}
    assert frozenset({"tsm_score", "vol_score"}) in grouped
    assert frozenset({"mr_score"}) in grouped

    pairs = overlap_pairs(corr, threshold=0.7)
    assert not pairs.empty
    assert set(pairs.loc[0, ["model_a", "model_b"]]) == {
        PERSPECTIVES_BY_KEY["tsm_score"].name,
        PERSPECTIVES_BY_KEY["vol_score"].name,
    }


def test_narrative_mentions_shared_information_and_conflicts(pipeline_result):
    report = consensus_report(pipeline_result, symbols=["MSR"])[0]
    assert "nhóm thông tin" in report.narrative
    assert "Không góc nhìn nào bị loại bỏ" in report.narrative or "độc lập với nhau" in report.narrative


def test_overview_and_views_table_shapes(pipeline_result):
    reports = consensus_report(pipeline_result)
    overview = consensus_overview(reports)
    assert len(overview) == len(reports)
    assert {"Mã", "Trạng thái", "Hướng tăng", "Hướng giảm"}.issubset(overview.columns)

    table = views_table(reports[0])
    assert len(table) == 9
    assert table["Vai trò"].nunique() == 3


def test_empty_input_returns_no_report():
    assert consensus_report(pd.DataFrame()) == []
