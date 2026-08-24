# Stock Quant

Khung phân tích định lượng cổ phiếu cho một hoặc nhiều mã, dùng dữ liệu Vnstock.

Trọng tâm của dự án là **Consensus Analysis**: đọc 9 mô hình như 9 góc nhìn độc lập
về cùng một cổ phiếu, rồi mô tả xem chúng đang đồng thuận, mâu thuẫn hay trung tính.

## Nguyên tắc

• Giữ nguyên 9 mô hình và công thức hiện tại
• Mỗi mô hình là một góc nhìn độc lập, không mô hình nào được ưu tiên hơn mô hình khác
• **Không có Composite Score.** Không cộng, không trung bình, không gán trọng số cho 9 Score
• Correlation chỉ dùng để phát hiện mức độ thông tin chung, không dùng để tự động loại bỏ mô hình
• Các con số do tầng Consensus tạo ra chỉ là **số lượng góc nhìn** trong từng nhóm

## Chín góc nhìn

| Góc nhìn | Nhóm | Vai trò | Câu hỏi mà mô hình trả lời |
| --- | --- | --- | --- |
| Time Series Momentum | Momentum | Hướng giá | Giá 20 và 60 phiên đang đi theo hướng nào và có tăng tốc không |
| Vol Adjusted Edge | Momentum trên đơn vị biến động | Hướng giá | Sau khi chia cho biến động, đà giá còn lại bao nhiêu |
| Mean Reversion | Mean Reversion | Hướng giá | Giá đang lệch bao xa khỏi trung bình ngắn hạn của chính nó |
| Monte Carlo | Monte Carlo | Hướng giá | Mô phỏng ngẫu nhiên 20 phiên tới cho xác suất tăng bao nhiêu |
| Trend Persistence | Trend Persistence | Bối cảnh | Chuỗi lợi nhuận đang nối tiếp hay triệt tiêu lẫn nhau |
| Range Expansion | Range Expansion | Bối cảnh | Biên độ hiện tại rộng hay hẹp so với 60 phiên gần nhất |
| OHLC Volatility | Volatility | Rủi ro | Mức biến động hiện tại đang ở đâu so với nền của chính nó |
| Tail Geometry | Tail Risk | Rủi ro | Các phiên cực đoan nghiêng về phía tăng hay phía giảm |
| Manipulation Guard | Market Integrity | Rủi ro | Gap, biên độ trong phiên và khối lượng có bất thường không |

Ba vai trò được tách bạch có chủ đích. Chỉ bốn góc nhìn hướng giá mới được dùng để
đếm đồng thuận về hướng. Bối cảnh và rủi ro được đọc riêng, và mâu thuẫn giữa các
vai trò cũng được ghi nhận, ví dụ hướng giá nghiêng về tăng trong khi rủi ro chưa
xác nhận.

## Consensus Analysis hoạt động thế nào

1. **Trạng thái từng góc nhìn.** Mỗi Score được so với ngưỡng riêng của mô hình đó
   và quy về ba trạng thái, kèm diễn giải bằng lời.
2. **Nhóm đồng thuận.** Các góc nhìn cùng vai trò và cùng trạng thái được gom lại.
   Cần ít nhất hai góc nhìn thì mới gọi là một nhóm đồng thuận.
3. **Mâu thuẫn.** Gồm mâu thuẫn trong nội bộ hướng giá và các mâu thuẫn giữa vai trò
   như đà tăng nhưng thiếu quán tính, biên độ mở rộng do biến động, hoặc dấu hiệu
   giao dịch bất thường.
4. **Trung tính.** Các góc nhìn chưa đủ mạnh để chọn phía được liệt kê riêng thay vì
   bị bỏ qua.
5. **Thông tin chung.** Ma trận correlation của chính mã đó được dùng để gom các góc
   nhìn có `|correlation|` vượt ngưỡng vào cùng một nhóm thông tin. Nhóm này nói lên
   rằng các thành viên đang mang thông tin gần giống nhau, nên sự đồng thuận giữa
   chúng không phải là nhiều xác nhận độc lập. Không mô hình nào bị loại bỏ.
6. **Market Narrative.** Toàn bộ kết quả trên được viết lại thành một đoạn ngắn giải
   thích vì sao các mô hình đang đồng thuận hoặc mâu thuẫn.

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
│   ├── regime.py
│   ├── risk.py
│   └── volatility.py
├── consensus/
│   ├── perspectives.py   # registry 9 góc nhìn
│   ├── overlap.py        # thông tin chung qua correlation
│   ├── narrative.py      # Market Narrative
│   └── report.py         # đồng thuận, mâu thuẫn, trung tính
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

Giao diện hỗ trợ cả **API miễn phí** qua thư viện `vnstock` và **API đã đăng ký** qua
`vnstock_data`, theo cùng kiến trúc Unified UI.

Nhập một mã:

```text
MSR
```

hoặc nhiều mã:

```text
MSR FPT HPG VIC
```

Mỗi mã có một tab riêng gồm trạng thái đồng thuận, Market Narrative, ba cột đồng
thuận / mâu thuẫn / trung tính, và thẻ của cả 9 góc nhìn xếp theo vai trò. Khi phân
tích nhiều mã, bảng tổng quan ở trên cùng chỉ chứa số đếm góc nhìn.

## Chạy dòng lệnh

```bash
python -m stock_quant.cli MSR FPT --start 2023-01-01 --end 2024-12-31
python -m stock_quant.cli MSR --start 2023-01-01 --end 2024-12-31 --mode registered
python -m stock_quant.cli MSR --start 2023-01-01 --end 2024-12-31 --scores-only
```

## Kiểm định

Pipeline nghiên cứu lưu Score theo mã và ngày, sau đó so sánh với lợi nhuận tương lai
5, 10, 20 và 60 phiên bằng Information Coefficient và Hit Ratio. Việc kiểm định này
đánh giá từng mô hình riêng lẻ, không tạo ra Score tổng hợp.

Đây là khung nghiên cứu ban đầu. Các công thức Score hiện tại là phiên bản mô phỏng để
dựng pipeline và cần được hiệu chuẩn bằng dữ liệu lịch sử trước khi dùng cho quyết định
đầu tư.

## Kiểm thử

```bash
pytest
```
