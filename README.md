# Stock Quant

Khung phân tích định lượng cổ phiếu cho một hoặc nhiều mã, dùng dữ liệu Vnstock.

## Mục tiêu

• Thu thập OHLCV cho nhiều mã
• Tạo đặc trưng giá và thanh khoản
• Chạy 9 nhóm mô hình: Monte Carlo, Time Series Momentum, Trend Persistence, Range Expansion, Mean Reversion, Manipulation Guard, OHLC Volatility, Tail Geometry và Vol Adjusted Edge
• Tạo lợi nhuận tương lai 5, 10, 20 và 60 phiên để kiểm định
• Kiểm tra tương quan giữa các Score để phát hiện trùng lặp thông tin
• Đánh giá Information Coefficient và Hit Ratio
• Phân tích một mã hoặc nhiều mã trong cùng một pipeline

## Cấu trúc

```text
stock_quant/
├── config.py
├── data/
│   ├── schema.py
│   ├── store.py
│   └── vnstock_client.py
├── features/
│   └── price_features.py
├── models/
│   ├── momentum.py
│   ├── persistence.py
│   ├── risk.py
│   └── volatility.py
├── research/
│   ├── evaluation.py
│   ├── redundancy.py
│   └── targets.py
└── analysis/
    └── pipeline.py
```

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy giao diện

```bash
streamlit run app.py
```

Nhập một mã:

```text
MSR
```

hoặc nhiều mã:

```text
MSR FPT HPG VIC
```

## Kiểm định

Pipeline nghiên cứu lưu Score theo mã và ngày, sau đó so sánh với lợi nhuận tương lai. Không cộng trực tiếp 9 Score để kết luận.

Correlation được dùng để nhận diện các mô hình có tín hiệu tương tự. Giá trị tuyệt đối của correlation từ 0,70 trở lên được đưa vào danh sách cần rà soát.

Đây là khung nghiên cứu ban đầu. Các công thức Score hiện tại là phiên bản mô phỏng để dựng pipeline và cần được hiệu chuẩn bằng dữ liệu lịch sử trước khi dùng cho quyết định đầu tư.
