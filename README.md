# Stock Quant

Khung phân tích định lượng cổ phiếu cho một hoặc nhiều mã, dùng dữ liệu Vnstock.

Dự án đọc 9 mô hình như 9 góc nhìn độc lập về cùng một cổ phiếu, qua bốn tầng:

| Tầng | Câu hỏi |
| --- | --- |
| **Current Signal** | Chín góc nhìn đang nói gì tại phiên gần nhất |
| **Score Impact** | Trong quá khứ, từng Score riêng lẻ tác động thế nào lên Future Return |
| **Correlation** | Các góc nhìn đang mang thông tin chung đến mức nào |
| **Consensus** | Chín góc nhìn đang đồng thuận, mâu thuẫn hay trung tính |

## Nguyên tắc

• Giữ nguyên 9 mô hình và công thức hiện tại
• Mỗi mô hình là một góc nhìn độc lập, không mô hình nào được ưu tiên hơn mô hình khác
• **Không có Composite Score.** Không cộng, không trung bình, không gán trọng số cho 9 Score
• **Không tự chọn trọng số.** Score Impact chỉ đo và mô tả, không đề xuất cách phối hợp Score
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

## Score Impact hoạt động thế nào

Consensus trả lời câu hỏi *hiện tại các mô hình đang nói gì*. Score Impact trả lời một
câu hỏi khác hẳn: *trong quá khứ, mỗi Score đứng một mình có liên quan gì tới lợi nhuận
về sau không*. Mỗi mô hình được đo riêng lẻ, không mô hình nào được cộng với mô hình khác.

1. **Future Return 5D, 20D, 60D.** Lợi nhuận của chính cổ phiếu đó sau 5, 20 và 60 phiên
   tính từ mỗi phiên trong lịch sử.
2. **Information Coefficient.** Tương quan hạng Spearman giữa Score tại phiên `t` và
   Future Return sau đó, tính cho từng Score và từng horizon. IC dương nghĩa là Score cao
   đi cùng lợi nhuận cao, IC âm nghĩa là ngược chiều, IC quanh 0 nghĩa là không đo được
   liên hệ nào.
3. **Quintile analysis.** Mỗi Score được chia thành 5 nhóm bằng nhau từ thấp tới cao, rồi
   tính Future Return trung bình, trung vị và tỉ lệ phiên dương của từng nhóm. Chênh lệch
   `Q5 − Q1` và mức đơn điệu cho biết quan hệ có đều đặn hay chỉ đến từ vài nhóm cá biệt.
   Khi phân tích nhiều mã, việc chia nhóm được làm trong nội bộ từng mã.
4. **Ổn định của IC theo thời gian.** IC của cả mẫu chỉ là một con số. Cửa sổ trượt tính
   lại IC theo thời gian và ghi nhận tỉ lệ cửa sổ giữ nguyên dấu cùng tỉ số giữa IC trung
   bình và độ phân tán của nó, rồi quy về một nhãn: *Ổn định*, *Tạm ổn định*, *Dao động*
   hay *Đảo dấu*.
5. **Biểu đồ.** Một biểu đồ cột Score → Future Return theo 5 nhóm quintile, và một biểu đồ
   đường IC theo thời gian với ba horizon trên cùng một trục.

Hai lưu ý khi đọc tầng này. Future Return 20D và 60D của các phiên liền nhau chồng lấn lên
nhau, nên số quan sát độc lập thấp hơn số dòng và p-value chỉ nên đọc như tham khảo. Và IC
là kết quả đo lường lịch sử của một mô hình đơn lẻ, nó không phải trọng số và không nói mô
hình nào nên được tin hơn mô hình nào.

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
├── impact/
│   ├── horizons.py       # Future Return 5D, 20D, 60D
│   ├── ic.py             # Information Coefficient từng Score
│   ├── quintiles.py      # chia Score thành 5 nhóm
│   ├── stability.py      # IC theo cửa sổ trượt
│   └── report.py         # tổng hợp Score Impact
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

Giao diện được chia thành bốn tab theo đúng bốn tầng đọc, mỗi tab lại có tab con cho
từng mã:

| Tab | Nội dung |
| --- | --- |
| **Current Signal** | Trạng thái đồng thuận, số đếm góc nhìn và thẻ của cả 9 góc nhìn xếp theo vai trò |
| **Score Impact** | Ma trận IC 9 Score × 3 horizon, bảng chi tiết theo horizon, hai biểu đồ và bảng quintile |
| **Correlation** | Nhóm thông tin chung, các cặp vượt ngưỡng và ma trận tương quan đầy đủ |
| **Consensus** | Market Narrative và ba cột đồng thuận / mâu thuẫn / trung tính |

Khi phân tích nhiều mã, Current Signal có thêm bảng tổng quan chỉ chứa số đếm góc nhìn,
còn Score Impact có thêm tab **Tất cả mã** đo IC riêng cho từng mã rồi lấy trung bình
giữa các mã. Đó là trung bình của IC, không phải trung bình của Score.

Thanh bên có hai tham số: ngưỡng `|correlation|` cho nhóm thông tin chung, và độ dài cửa
sổ trượt dùng khi đo tính ổn định của IC.

## Chạy dòng lệnh

```bash
python -m stock_quant.cli MSR FPT --start 2023-01-01 --end 2024-12-31
python -m stock_quant.cli MSR --start 2023-01-01 --end 2024-12-31 --mode registered
python -m stock_quant.cli MSR --start 2023-01-01 --end 2024-12-31 --scores-only
python -m stock_quant.cli MSR --start 2023-01-01 --end 2024-12-31 --impact
```

## Kiểm định

Pipeline nghiên cứu lưu Score theo mã và ngày, sau đó so sánh với lợi nhuận tương lai
5, 10, 20 và 60 phiên bằng Information Coefficient và Hit Ratio. Tầng Score Impact đọc
lại chính panel đó ở ba horizon 5, 20 và 60 phiên. Cả hai đều đánh giá từng mô hình
riêng lẻ và không tạo ra Score tổng hợp.

Đây là khung nghiên cứu ban đầu. Các công thức Score hiện tại là phiên bản mô phỏng để
dựng pipeline và cần được hiệu chuẩn bằng dữ liệu lịch sử trước khi dùng cho quyết định
đầu tư.

## Kiểm thử

```bash
pytest
```
