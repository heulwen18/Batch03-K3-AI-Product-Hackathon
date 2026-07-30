# Codebase — Bản đồ Vướng Mắc Lớp (Class Friction Map)

Tương ứng lát cắt trong `spec.md` §4. Trạng thái hiện tại: **Khối 1 + Khối 2 + Khối 3 xong**, Agent A (chatbot demo ReAct) chưa build.

## Kiến trúc

```
data_prep.py         -- đọc CSV chatlog, ghép turn, group theo ngày (giờ VN)         [KHÔNG AI]
transcript_index.py  -- index keyword-overlap trên 700 đoạn transcript              [KHÔNG AI]
signals.py           -- KHỐI 1: rule-based friction detection (đúng định nghĩa       [KHÔNG AI]
                         đã chốt ở spec.md §1: lặp trang≥3 / đổi diễn đạt /
                         give_direct_answer / rating-down-rồi-bỏ-cuộc)
classify_friction.py -- KHỐI 2: LỜI GỌI AI THẬT — phân loại friction theo khái       [AI THẬT]
                         niệm + nguyên nhân (dạy chưa rõ / tutor tìm sai / chưa đủ
                         dữ liệu), dùng tool_use ép JSON schema, không tự parse
                         text lỏng lẻo
dashboard.py          -- KHỐI 3: UI Streamlit cho giảng viên — chọn ngày, xem        [KHÔNG AI —
                         số liệu Khối 1 tức thời, bấm nút mới chạy Khối 2 (dry-run     chỉ điều
                         mặc định để không tốn quota, chuyển "Gọi AI thật" khi cần)    phối hiển
                                                                                       thị]
```

**Chưa build:**
- Agent A — chatbot demo ReAct/tool-calling cho học viên chat live (xem kế hoạch đã thống nhất)

## Chạy dashboard

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

Mặc định mở ở chế độ **Dry-run** (không gọi AI, chỉ hiện payload sẽ gửi) — an toàn để demo thử nhiều lần không tốn quota. Khi cần chạy thật: đổi sang "Gọi AI thật" ở sidebar + nhập `ANTHROPIC_API_KEY` (hoặc set biến môi trường trước khi chạy `streamlit run`).

Đã test: app khởi động không lỗi (health check `_stcore/health` → `ok`, log sạch), Khối 1 chạy đúng trên toàn bộ 9 ngày có data.

## Cách chạy thử

```bash
pip install -r requirements.txt

# Xem các ngày có data
python3 data_prep.py

# Khối 1 riêng — xem tỷ lệ friction mỗi ngày (không cần API key)
python3 signals.py

# Khối 2 — mặc định DRY RUN (không gọi API, chỉ in payload sẽ gửi để kiểm tra trước khi tốn quota)
python3 classify_friction.py 2026-07-27

# Khối 2 — gọi AI THẬT (cần biến môi trường ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-...
python3 classify_friction.py 2026-07-27 --live
```

## Định nghĩa "friction" (đã chốt, khớp spec.md §1 — không đổi tự tiện, đúng luật quality bar)

Một hội thoại được gắn cờ friction khi có **≥1** trong các tín hiệu hành vi sau (KHÔNG dùng từ khoá cảm xúc — chỉ ~1% mẫu, quá hiếm):

| Tín hiệu | Ngưỡng |
|---|---|
| Lặp lại cùng 1 trang | ≥3 lần trong 1 hội thoại |
| Đổi cách diễn đạt hỏi lại cùng khái niệm | ≥1 lần |
| Tutor phải `give_direct_answer` | ≥1 lần |
| Rating "down" ở turn cuối rồi không hỏi tiếp | có |

Tín hiệu "mất tập trung" (chào hỏi/cụt/rỗng) được tính riêng (`offtopic_count`) nhưng **không** góp vào `friction_flag` — đúng non-goal đã ghi trong spec.md §4 (tín hiệu này yếu, dễ hiểu sai).

## Việc còn thiếu để chạy end-to-end (đưa vào eval/ + golden set)

- [ ] Chạy `--live` thật với API key, đọc kết quả tay để kiểm tra model có tuân thủ đúng 3 nhãn nguyên nhân không
- [ ] Trích ≥20 case cho golden set từ output Khối 1 (đã có sẵn cấu trúc `friction_cases`) + 2 người chấm độc lập so kết quả
- [ ] Ghép Khối 3 (UI) để demo bấm được
