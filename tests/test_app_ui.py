"""Smoke test cho giao diện Streamlit, chạy trực tiếp app.py qua AppTest."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

from stock_quant.analysis import run_signal_pipeline  # noqa: E402
from tests.test_consensus import make_prices  # noqa: E402

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def build_app(symbols=("MSR", "FPT")) -> AppTest:
    prices = make_prices(symbols=symbols)
    result = run_signal_pipeline(prices, monte_carlo_simulations=200, monte_carlo_stride=20)

    app = AppTest.from_file(APP_PATH, default_timeout=120)
    app.session_state["result"] = result
    app.session_state["symbols"] = list(symbols)
    app.session_state["counts"] = prices.groupby("symbol").size().rename("Số phiên")
    return app.run()


def test_app_renders_landing_page_without_data():
    app = AppTest.from_file(APP_PATH, default_timeout=120).run()
    assert not app.exception
    assert any("bấm Phân tích" in item.value for item in app.info)


def test_app_renders_consensus_for_multiple_symbols():
    app = build_app()
    assert not app.exception

    headers = [item.value for item in app.subheader]
    assert "Tổng quan đồng thuận" in headers
    assert "Chi tiết theo mã" in headers

    labels = [tab.label for tab in app.tabs]
    assert "MSR" in labels and "FPT" in labels

    narratives = [item.value for item in app.info]
    assert len(narratives) >= 2
    assert all("không phải khuyến nghị đầu tư" in text for text in narratives)


def test_app_renders_single_symbol_without_overview():
    app = build_app(symbols=("MSR",))
    assert not app.exception
    assert "Tổng quan đồng thuận" not in [item.value for item in app.subheader]
    assert [tab.label for tab in app.tabs] == ["MSR"]


def test_app_never_shows_a_composite_score():
    app = build_app()
    rendered = " ".join(str(element.value) for element in app.markdown) + " ".join(
        str(element.value) for element in app.info
    )
    assert "Composite" not in rendered or "Không có Composite Score" in rendered
    assert "Điểm tổng hợp" not in rendered
