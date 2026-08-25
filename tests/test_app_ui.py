"""Smoke test cho giao diện Streamlit, chạy trực tiếp app.py qua AppTest."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

from stock_quant.analysis import run_signal_pipeline  # noqa: E402
from tests.test_consensus import make_prices  # noqa: E402

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")

LAYERS = ("Current Signal", "Score Impact", "Correlation", "Consensus")


def build_app(symbols=("MSR", "FPT"), periods=300) -> AppTest:
    prices = make_prices(symbols=symbols, periods=periods)
    result = run_signal_pipeline(prices, monte_carlo_simulations=200, monte_carlo_stride=20)

    app = AppTest.from_file(APP_PATH, default_timeout=300)
    app.session_state["result"] = result
    app.session_state["symbols"] = list(symbols)
    app.session_state["counts"] = prices.groupby("symbol").size().rename("Số phiên")
    return app.run()


def rendered_text(app: AppTest) -> str:
    parts = [str(item.value) for item in app.markdown]
    parts += [str(item.value) for item in app.info]
    parts += [str(item.value) for item in app.caption]
    parts += [str(item.label) for item in app.tabs]
    parts += [str(item.label) for item in app.get("expander")]
    return " ".join(parts)


def charts(app: AppTest) -> list:
    """Biểu đồ được vẽ, tên phần tử khác nhau giữa các phiên bản Streamlit."""
    for name in ("vega_lite_chart", "arrow_vega_lite_chart"):
        found = list(app.get(name))
        if found:
            return found
    return []


@pytest.fixture(scope="module")
def app():
    return build_app()


def test_app_renders_landing_page_without_data():
    app = AppTest.from_file(APP_PATH, default_timeout=300).run()
    assert not app.exception
    assert any("bấm Phân tích" in item.value for item in app.info)


def test_app_renders_the_four_reading_layers(app):
    assert not app.exception
    labels = [tab.label for tab in app.tabs]
    for layer in LAYERS:
        assert layer in labels


def test_every_layer_has_a_tab_for_each_symbol(app):
    labels = [tab.label for tab in app.tabs]
    # Bốn tầng, mỗi tầng một tab cho mỗi mã; Score Impact có thêm tab "Tất cả mã".
    assert labels.count("MSR") == len(LAYERS)
    assert labels.count("FPT") == len(LAYERS)
    assert labels.count("Tất cả mã") == 1


def test_current_signal_layer_shows_the_nine_views(app):
    text = rendered_text(app)
    assert "Chín góc nhìn độc lập" in text
    assert "Tổng quan đồng thuận" in text


def test_score_impact_layer_shows_ic_quintile_and_stability(app):
    text = rendered_text(app)
    assert "Information Coefficient theo từng Score và từng horizon" in text
    assert "Score → Future Return" in text
    assert "IC theo thời gian" in text
    assert "Quintile analysis" in text
    assert "Tính ổn định của IC theo thời gian" in text


def test_score_impact_layer_draws_both_charts(app):
    # Mỗi phạm vi vẽ một biểu đồ quintile và một biểu đồ IC theo thời gian.
    assert len(charts(app)) == 2 * 3


def test_correlation_layer_is_kept(app):
    text = rendered_text(app)
    assert "Ma trận tương quan" in text
    assert "Nhóm thông tin" in text
    assert "Không mô hình nào bị loại bỏ vì tương quan cao." in text


def test_consensus_layer_shows_narrative_and_groups(app):
    text = rendered_text(app)
    assert "Market Narrative" in text
    assert "Nhóm đồng thuận" in text
    assert "Mâu thuẫn" in text

    narratives = [item.value for item in app.info if "khuyến nghị đầu tư" in str(item.value)]
    assert len(narratives) >= 2


def test_app_renders_single_symbol_without_overview_tables():
    app = build_app(symbols=("MSR",))
    assert not app.exception
    labels = [tab.label for tab in app.tabs]
    assert labels.count("MSR") == len(LAYERS)
    assert "Tất cả mã" not in labels
    assert "Tổng quan đồng thuận" not in rendered_text(app)


def test_app_never_shows_a_composite_score_or_a_weight(app):
    text = rendered_text(app)
    assert "Composite" not in text or "Không có Composite Score" in text
    assert "Điểm tổng hợp" not in text
    assert "trọng số" not in text or "không có trọng số" in text.lower()
