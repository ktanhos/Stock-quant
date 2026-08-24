import numpy as np
import pandas as pd
import pytest

from stock_quant.analysis import run_signal_pipeline
from stock_quant.impact import (
    IMPACT_HORIZONS,
    assign_buckets,
    effective_window,
    ic_stability,
    impact_highlights,
    impact_overview,
    impact_table,
    quintile_chart_frame,
    quintile_display,
    quintile_profile,
    quintile_summary,
    quintile_table,
    rolling_chart_frame,
    rolling_ic,
    score_impact,
    spearman_ic,
    stability_table,
    symbol_ic_table,
)
from stock_quant.impact.horizons import forward_return_column
from tests.test_consensus import make_prices

SCORE_KEY = "tsm_score"
OTHER_KEY = "mr_score"


def synthetic_frame(
    periods: int = 300,
    slope: float = 1.0,
    noise: float = 0.2,
    symbol: str = "AAA",
    seed: int = 7,
    flip: bool = False,
) -> pd.DataFrame:
    """Khung dữ liệu nhân tạo với quan hệ Score → Future Return đã biết trước."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-03", periods=periods, freq="B")
    score = rng.normal(size=periods) * 20.0
    direction = np.ones(periods)
    if flip:
        direction[periods // 2:] = -1.0

    frame = {"symbol": symbol, "date": dates, SCORE_KEY: score, OTHER_KEY: rng.normal(size=periods)}
    for horizon in IMPACT_HORIZONS:
        shock = rng.normal(size=periods) * noise
        frame[forward_return_column(horizon)] = (
            direction * slope * score / 1000.0 + shock / 100.0
        )
    return pd.DataFrame(frame)


@pytest.fixture(scope="module")
def pipeline_result():
    prices = make_prices(symbols=("MSR", "FPT"), periods=300)
    return run_signal_pipeline(prices, monte_carlo_simulations=200, monte_carlo_stride=20)


# ----------------------------------------------------------------------- 1. Future Return horizons


def test_pipeline_provides_the_three_impact_horizons(pipeline_result):
    for horizon in (5, 20, 60):
        column = forward_return_column(horizon)
        assert column in pipeline_result.columns
        assert pipeline_result[column].notna().any()


def test_impact_horizons_are_five_twenty_and_sixty():
    assert IMPACT_HORIZONS == (5, 20, 60)


# --------------------------------------------------------------------- 2. Information Coefficient


def test_ic_table_covers_every_available_score_and_horizon(pipeline_result):
    history = pipeline_result[pipeline_result["symbol"] == "MSR"]
    table = symbol_ic_table(history)
    scores = table["score_key"].nunique()
    assert scores >= 8
    assert len(table) == scores * len(IMPACT_HORIZONS)
    assert set(table["horizon"]) == set(IMPACT_HORIZONS)
    assert table["ic"].notna().any()


def test_ic_recovers_a_known_positive_relationship():
    frame = synthetic_frame()
    ic, p_value, count = spearman_ic(frame[SCORE_KEY], frame[forward_return_column(20)])
    assert count == 300
    assert ic > 0.5
    assert p_value < 0.01


def test_ic_flips_sign_with_the_relationship():
    positive = symbol_ic_table(synthetic_frame(slope=1.0))
    negative = symbol_ic_table(synthetic_frame(slope=-1.0))
    for horizon in IMPACT_HORIZONS:
        up = positive[(positive["score_key"] == SCORE_KEY) & (positive["horizon"] == horizon)]
        down = negative[(negative["score_key"] == SCORE_KEY) & (negative["horizon"] == horizon)]
        assert float(up["ic"].iloc[0]) > 0.4
        assert float(down["ic"].iloc[0]) < -0.4


def test_ic_is_missing_when_observations_are_too_few():
    short = synthetic_frame(periods=12)
    table = symbol_ic_table(short)
    assert table["ic"].isna().all()
    assert (table["observations"] <= 12).all()


def test_unrelated_score_has_no_meaningful_ic():
    table = symbol_ic_table(synthetic_frame(periods=400, noise=1.0))
    other = table[table["score_key"] == OTHER_KEY]
    assert other["ic"].abs().max() < 0.2


# -------------------------------------------------------------------------- 3. Quintile analysis


def test_assign_buckets_creates_five_equal_groups():
    buckets = assign_buckets(pd.Series(np.arange(100.0)))
    counts = buckets.value_counts()
    assert sorted(buckets.dropna().unique()) == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert counts.min() == counts.max() == 20


def test_quintiles_are_monotonic_for_a_monotonic_relationship():
    table = quintile_table(synthetic_frame(noise=0.05), SCORE_KEY, 20)
    assert len(table) == 5
    returns = table.sort_values("bucket")["mean_return"].to_numpy()
    assert np.all(np.diff(returns) > 0)

    summary = quintile_summary(quintile_profile(synthetic_frame(noise=0.05)))
    row = summary[(summary["score_key"] == SCORE_KEY) & (summary["horizon"] == 20)].iloc[0]
    assert row["spread"] > 0
    assert row["monotonicity"] == pytest.approx(1.0)


def test_quintiles_are_split_inside_each_symbol():
    left = synthetic_frame(symbol="AAA", seed=1)
    right = synthetic_frame(symbol="BBB", seed=2)
    right[SCORE_KEY] = right[SCORE_KEY] + 500.0  # mức Score lệch hẳn so với mã kia

    table = quintile_table(pd.concat([left, right], ignore_index=True), SCORE_KEY, 20)
    assert len(table) == 5
    # Mỗi mã đóng góp đúng một phần vào mỗi nhóm nên nhóm nào cũng có 120 quan sát.
    assert table["observations"].nunique() == 1


def test_quintile_profile_covers_every_score_and_horizon(pipeline_result):
    profile = quintile_profile(pipeline_result[pipeline_result["symbol"] == "MSR"])
    assert not profile.empty
    assert set(profile["horizon"]) == set(IMPACT_HORIZONS)
    for (_, _), group in profile.groupby(["score_key", "horizon"]):
        assert len(group) == 5


def test_quintile_table_is_empty_without_enough_rows():
    assert quintile_table(synthetic_frame(periods=10), SCORE_KEY, 20).empty


# ------------------------------------------------------------------------------ 4. IC stability


def test_effective_window_shrinks_for_short_history():
    assert effective_window(400, 120) == 120
    assert effective_window(160, 120) == 80
    assert effective_window(50, 120) == 40


def test_rolling_ic_is_stable_for_a_constant_relationship():
    rolling = rolling_ic(synthetic_frame(periods=400, noise=0.1))
    stability = ic_stability(rolling)
    row = stability[(stability["score_key"] == SCORE_KEY) & (stability["horizon"] == 20)].iloc[0]
    assert row["windows"] >= 3
    assert row["sign_consistency"] == pytest.approx(1.0)
    assert row["label"] == "Ổn định"


def test_rolling_ic_detects_a_relationship_that_flips_sign():
    rolling = rolling_ic(synthetic_frame(periods=600, noise=0.05, flip=True), window=100)
    stability = ic_stability(rolling)
    row = stability[(stability["score_key"] == SCORE_KEY) & (stability["horizon"] == 20)].iloc[0]
    assert row["sign_consistency"] < 0.95
    assert row["label"] != "Ổn định"


def test_rolling_ic_is_empty_when_history_is_too_short():
    assert rolling_ic(synthetic_frame(periods=40)).empty


def test_rolling_ic_averages_across_symbols():
    frame = pd.concat(
        [synthetic_frame(symbol="AAA", seed=1), synthetic_frame(symbol="BBB", seed=2)],
        ignore_index=True,
    )
    rolling = rolling_ic(frame)
    assert not rolling.empty
    assert rolling["symbols"].max() == 2


# ------------------------------------------------------------------------------- 5. Chart frames


def test_quintile_chart_frame_has_five_rows_and_three_horizons():
    profile = quintile_profile(synthetic_frame())
    chart = quintile_chart_frame(profile, SCORE_KEY)
    assert list(chart.index) == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert len(chart.columns) == len(IMPACT_HORIZONS)


def test_rolling_chart_frame_is_indexed_by_date():
    rolling = rolling_ic(synthetic_frame(periods=400))
    chart = rolling_chart_frame(rolling, SCORE_KEY)
    assert not chart.empty
    assert chart.index.name == "Ngày"
    assert all(column.startswith("IC ") for column in chart.columns)


def test_chart_frames_are_empty_for_an_unknown_score():
    profile = quintile_profile(synthetic_frame())
    assert quintile_chart_frame(profile, "vsf_score").empty
    assert rolling_chart_frame(rolling_ic(synthetic_frame()), "vsf_score").empty


# ------------------------------------------------------------------------------ 6. Score Impact


def test_score_impact_builds_every_section(pipeline_result):
    impact = score_impact(pipeline_result, symbol="MSR")
    assert impact.label == "MSR"
    assert impact.has_data
    assert not impact.ic.empty
    assert not impact.quintiles.empty
    assert not impact.quintile_spread.empty
    assert not impact.rolling.empty
    assert not impact.stability.empty
    assert impact.observations > 0

    matrix = impact.ic_matrix()
    assert list(matrix.columns) == ["5D", "20D", "60D"]
    assert len(matrix) >= 8


def test_score_impact_panel_averages_ic_across_symbols(pipeline_result):
    panel = score_impact(pipeline_result)
    assert panel.label == "Tất cả mã"
    assert panel.scope == "panel"
    assert set(panel.symbols) == {"MSR", "FPT"}
    assert "symbols" in panel.ic.columns
    assert panel.ic["symbols"].max() == 2


def test_score_impact_does_not_mutate_the_input(pipeline_result):
    before = pipeline_result.copy()
    score_impact(pipeline_result, symbol="MSR")
    pd.testing.assert_frame_equal(pipeline_result, before)


def test_score_impact_reports_short_history_instead_of_failing():
    impact = score_impact(synthetic_frame(periods=15), symbol="AAA")
    assert not impact.has_data
    assert any("chưa đủ" in note.lower() for note in impact.notes)
    assert impact_table(impact, 20).empty or impact_table(impact, 20)["IC"].isna().all()


def test_score_impact_on_empty_frame():
    impact = score_impact(pd.DataFrame(columns=["symbol", "date"]), symbol="AAA")
    assert not impact.has_data
    assert impact.notes


def test_impact_table_reads_ic_quintile_and_stability(pipeline_result):
    impact = score_impact(pipeline_result, symbol="MSR")
    table = impact_table(impact, 20)
    assert {"Góc nhìn", "IC", "Q5 − Q1 (%)", "Đơn điệu", "Ổn định"}.issubset(table.columns)
    assert len(table) == impact.ic["score_key"].nunique()

    assert not stability_table(impact, 20).empty
    assert not quintile_display(impact, SCORE_KEY, 20).empty


def test_impact_highlights_cover_every_horizon_and_stay_descriptive(pipeline_result):
    lines = impact_highlights(score_impact(pipeline_result, symbol="MSR"))
    joined = " ".join(lines)
    for horizon in ("5D", "20D", "60D"):
        assert horizon in joined
    assert "không phải trọng số" in joined
    assert "khuyến nghị" in joined


def test_impact_overview_lists_the_strongest_measured_score(pipeline_result):
    impacts = [score_impact(pipeline_result, symbol=s) for s in ("MSR", "FPT")]
    overview = impact_overview(impacts)
    assert list(overview["Phạm vi"]) == ["MSR", "FPT"]
    for horizon in ("5D", "20D", "60D"):
        assert f"IC {horizon} cao nhất" in overview.columns


# ------------------------------------------------------- 7. Ranh giới: không Composite, không trọng số


def test_impact_layer_never_produces_a_composite_or_a_weight(pipeline_result):
    impact = score_impact(pipeline_result, symbol="MSR")
    banned = ("composite", "weight", "trọng số", "total_score", "final_score")
    frames = (
        impact.ic,
        impact.quintiles,
        impact.quintile_spread,
        impact.rolling,
        impact.stability,
        impact_table(impact, 20),
        stability_table(impact, 20),
    )
    for frame in frames:
        for column in frame.columns:
            assert not any(word in str(column).lower() for word in banned), column


def test_cli_prints_the_impact_layer(pipeline_result, capsys):
    from stock_quant.cli import print_impact

    print_impact(pipeline_result, ["msr"], 120)
    output = capsys.readouterr().out
    assert "Score Impact · MSR" in output
    assert "Information Coefficient theo horizon" in output
    for horizon in ("5D", "20D", "60D"):
        assert f"Chi tiết tại horizon {horizon}" in output


def test_impact_layer_keeps_all_nine_scores(pipeline_result):
    impact = score_impact(pipeline_result, symbol="MSR")
    keys = set(impact.ic["score_key"])
    # Mọi Score có dữ liệu đều được đo, kể cả khi IC của nó bằng 0.
    for key in ("tsm_score", "vol_score", "mr_score", "vrh_score", "exp_score", "vsf_score",
                "tail_score", "man_score"):
        assert key in keys
