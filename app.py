import streamlit as st

from stock_quant.analysis import latest_analysis, run_signal_pipeline
from stock_quant.data import VnstockClient, validate_price_frame
from stock_quant.research import correlation_matrix, highly_correlated_pairs


st.set_page_config(page_title="Stock Quant", layout="wide")
st.title("Stock Quant")
st.caption("Phân tích một hoặc nhiều cổ phiếu bằng 9 mô hình")

api_key = st.text_input(
    "Vnstock API Key",
    type="password",
    help="Khóa chỉ được dùng trong phiên hiện tại và không được ghi vào GitHub.",
)

symbols_text = st.text_input("Mã cổ phiếu", value="MSR")
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
        with st.spinner("Đang tải dữ liệu và chạy phân tích..."):
            client = VnstockClient(api_key=api_key or None)
            prices = client.fetch_price_history(symbols, str(start), str(end))

        validation = validate_price_frame(prices)
        if not validation.valid:
            st.error("Dữ liệu không hợp lệ: " + "; ".join(validation.errors))
            st.stop()

        if prices.empty:
            st.warning("Không có dữ liệu trả về cho mã và khoảng thời gian đã chọn")
            st.stop()

        result = run_signal_pipeline(prices)

    except Exception as exc:
        st.error(f"Không thể tải hoặc phân tích dữ liệu: {exc}")
        st.stop()

    st.subheader("Phân tích hiện tại")
    st.dataframe(latest_analysis(result, symbols), use_container_width=True)

    st.subheader("Tương quan giữa các Score")
    corr = correlation_matrix(result)
    st.dataframe(corr, use_container_width=True)

    pairs = highly_correlated_pairs(corr)
    if pairs.empty:
        st.info("Chưa phát hiện cặp Score có tương quan tuyệt đối từ 0,70 trở lên")
    else:
        st.warning("Các Score có tương quan cao")
        st.dataframe(pairs, use_container_width=True)
