import streamlit as st

from stock_quant.analysis import latest_analysis, run_signal_pipeline
from stock_quant.data import VnstockClient, validate_price_frame
from stock_quant.research import correlation_matrix, highly_correlated_pairs


st.set_page_config(page_title="Stock Quant", layout="wide")
st.title("Stock Quant")
st.caption("Phân tích một hoặc nhiều cổ phiếu bằng 9 mô hình")

data_mode = st.radio(
    "Nguồn dữ liệu",
    options=["API miễn phí", "API đã đăng ký"],
    horizontal=True,
)

registered_ready = VnstockClient.registered_package_available()

if data_mode == "API miễn phí":
    st.caption(
        "Sử dụng thư viện vnstock. Dữ liệu lịch sử được gọi theo từng đoạn "
        "để tránh giới hạn số lượng nến trong một lần truy vấn."
    )
else:
    st.text_input(
        "API Key đã đăng ký",
        type="password",
        disabled=True,
        placeholder="API Key được quản lý bởi vnstock_data",
    )

    if registered_ready:
        st.success(
            "Đã phát hiện vnstock_data trong môi trường hiện tại. "
            "Có thể sử dụng nguồn dữ liệu đã đăng ký."
        )
    else:
        st.error(
            "Chưa phát hiện vnstock_data trong Codespaces. "
            "API Key hợp lệ không thể thay thế thư viện dữ liệu đã đăng ký."
        )
        st.caption(
            "Chọn API miễn phí để chạy ngay. Chế độ API đã đăng ký chỉ hoạt động "
            "sau khi vnstock_data được cài vào đúng môi trường Python đang chạy Streamlit."
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

    if data_mode == "API đã đăng ký" and not registered_ready:
        st.error(
            "Không thể gọi API đã đăng ký vì vnstock_data chưa được cài "
            "trong môi trường Streamlit hiện tại."
        )
        st.stop()

    mode = "registered" if data_mode == "API đã đăng ký" else "free"

    try:
        with st.spinner("Đang tải dữ liệu..."):
            client = VnstockClient(mode=mode)
            prices = client.fetch_price_history(
                symbols,
                str(start),
                str(end),
            )

        validation = validate_price_frame(prices)
        if not validation.valid:
            st.error(
                "Dữ liệu không hợp lệ: "
                + "; ".join(validation.errors)
            )
            st.stop()

        if prices.empty:
            st.warning(
                "Không có dữ liệu trả về cho mã và khoảng thời gian đã chọn"
            )
            st.stop()

        counts = prices.groupby("symbol").size().rename("observations")
        st.subheader("Kiểm tra dữ liệu đầu vào")
        st.dataframe(counts.to_frame(), use_container_width=True)

        insufficient = counts[counts < 130]
        if not insufficient.empty:
            detail = ", ".join(
                f"{symbol}: {count} phiên"
                for symbol, count in insufficient.items()
            )
            st.warning(
                "Một số mã chưa đủ lịch sử cho toàn bộ mô hình: "
                + detail
            )

        with st.spinner("Đang chạy 9 mô hình..."):
            result = run_signal_pipeline(prices)

    except Exception as exc:
        st.error(f"Không thể tải hoặc phân tích dữ liệu: {exc}")
        st.stop()

    st.subheader("Phân tích hiện tại")
    st.caption(
        "Future Return tại ngày mới nhất không có giá trị vì chưa tồn tại dữ liệu tương lai."
    )
    st.dataframe(
        latest_analysis(result, symbols),
        use_container_width=True,
    )

    st.subheader("Tương quan giữa các Score")
    corr = correlation_matrix(result)
    valid_scores = corr.dropna(how="all").index.tolist()

    if len(valid_scores) < 2:
        st.warning(
            "Chưa đủ quan sát hợp lệ để tính tương quan giữa các Score."
        )
    else:
        corr_display = corr.loc[valid_scores, valid_scores]
        st.dataframe(corr_display, use_container_width=True)

        pairs = highly_correlated_pairs(corr_display)
        if pairs.empty:
            st.info(
                "Chưa phát hiện cặp Score có tương quan tuyệt đối từ 0,70 trở lên"
            )
        else:
            st.warning("Các Score có tương quan cao")
            st.dataframe(pairs, use_container_width=True)
