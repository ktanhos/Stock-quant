import streamlit as st

from stock_quant.analysis import latest_analysis, run_signal_pipeline
from stock_quant.data import VnstockClient, validate_price_frame
from stock_quant.research import correlation_matrix, highly_correlated_pairs


st.set_page_config(page_title="Stock Quant", layout="wide")
st.title("Stock Quant")
st.caption("Phân tích một hoặc nhiều cổ phiếu bằng 9 mô hình")

st.info(
    "Phiên bản hiện tại dùng Vnstock 4 Unified UI để lấy OHLCV. "
    "Theo tài liệu chính thức, dữ liệu OHLCV cơ bản của bản cộng đồng không cần nhập API Key."
)

symbols_text = st.text_input("Mã cổ phiếu", value="VIC")
start = st.date_input("Ngày bắt đầu", value=None)
end = st.date_input("Ngày kết thúc", value=None)

if st.button("Tải dữ liệu và phân tích"):
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

    try:
        with st.spinner("Đang tải dữ liệu..."):
            client = VnstockClient()
            prices = client.fetch_price_history(symbols, str(start), str(end))

        validation = validate_price_frame(prices)
        if not validation.valid:
            st.error("Dữ liệu không hợp lệ: " + "; ".join(validation.errors))
            st.stop()

        if prices.empty:
            st.warning("Không có dữ liệu trả về cho mã và khoảng thời gian đã chọn")
            st.stop()

        counts = prices.groupby("symbol").size().rename("observations")
        st.subheader("Kiểm tra dữ liệu đầu vào")
        st.dataframe(counts.to_frame(), use_container_width=True)

        insufficient = counts[counts < 130]
        if not insufficient.empty:
            symbols_text_list = ", ".join(
                f"{symbol}: {count} phiên" for symbol, count in insufficient.items()
            )
            st.warning(
                "Một số mã chưa có đủ lịch sử cho toàn bộ 9 mô hình. "
                "Khuyến nghị tối thiểu 130 phiên: " + symbols_text_list
            )

        with st.spinner("Đang chạy 9 mô hình..."):
            result = run_signal_pipeline(prices)

    except Exception as exc:
        st.error(f"Không thể tải hoặc phân tích dữ liệu: {exc}")
        st.stop()

    st.subheader("Phân tích hiện tại")
    st.caption(
        "Các chỉ số có giá trị None khi chưa đủ dữ liệu lịch sử cho cửa sổ tính toán. "
        "Future Return tại ngày mới nhất luôn chưa có dữ liệu vì chưa có các phiên tương lai."
    )
    st.dataframe(latest_analysis(result, symbols), use_container_width=True)

    st.subheader("Tương quan giữa các Score")
    corr = correlation_matrix(result)
    valid_scores = corr.dropna(how="all").index.tolist()

    if len(valid_scores) < 2:
        st.warning(
            "Chưa đủ quan sát hợp lệ để tính tương quan giữa các Score. "
            "Hãy mở rộng khoảng thời gian dữ liệu."
        )
    else:
        corr_display = corr.loc[valid_scores, valid_scores]
        st.dataframe(corr_display, use_container_width=True)

        pairs = highly_correlated_pairs(corr_display)
        if pairs.empty:
            st.info("Chưa phát hiện cặp Score có tương quan tuyệt đối từ 0,70 trở lên")
        else:
            st.warning("Các Score có tương quan cao")
            st.dataframe(pairs, use_container_width=True)
