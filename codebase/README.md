# AI Learning Analytics Copilot

Web app duy nhất (Streamlit, chạy local) gồm 2 phía của cùng một vòng lặp dữ liệu:
**học viên chat với AI Tutor** → hội thoại được ghi lại → **giảng viên/TA xem dashboard**
để biết cả lớp đang vướng ở khái niệm nào và nên làm gì tiếp.

Điều hướng sidebar 4 trang: **📡 Live Dashboard** (KPI + top vấn đề + khuyến nghị) ·
**💬 Conversations** (đọc nguyên văn + phân tích từng hội thoại) · **📑 Reports** (tổng hợp
theo tuần, so sánh tuần trước, xuất báo cáo) · **🎓 Chat AI Tutor**. Dữ liệu gom theo **tuần**
— không giới hạn số buổi, data thêm ngày/tuần mới sẽ tự xuất hiện.

```bash
pip install -r requirements.txt
streamlit run app.py        # mở http://localhost:8501
```

API key đặt trong `codebase/.env` (không commit — đã nằm trong `.gitignore`):

```env
GROQ_API_KEY = gsk_...
```

## App có gì — 3 tab

### 🧑‍🎓 Chat với AI Tutor (học viên)

- Chat hỏi đáp trên nội dung **6 buổi giảng được cấp** (700 đoạn transcript có mã trích dẫn).
- **Upload slide/tài liệu riêng** (PDF/PPTX/TXT/MD) — tutor sẽ CHỈ trả lời dựa trên file vừa
  upload, mỗi trang PDF/slide PPTX là 1 đơn vị trích dẫn. File toàn ảnh scan sẽ báo lỗi rõ ràng
  (bản demo không làm OCR).
- Nhập số trang đang xem để mô phỏng thao tác "bôi đen đoạn tài liệu rồi hỏi" của VLearn thật.
- Mỗi câu trả lời kèm mục **"📚 Nguồn đã tra cứu"**: mã đoạn, độ khớp và trích đoạn gốc — người
  dùng tự kiểm chứng được, không phải tin chay.
- Nguyên tắc cốt lõi: **không tìm thấy căn cứ thì từ chối trung thực, không bịa** từ kiến thức nền.

### 📊 Dashboard Giảng viên/TA

- **Xu hướng theo ngày**: % hội thoại rơi vào từng nhóm vướng mắc qua toàn bộ lịch sử, kèm tổng
  số hội thoại mỗi ngày (ngày mẫu nhỏ thì % kém tin cậy — có cảnh báo riêng khi < 20 hội thoại).
- **Số liệu trong ngày**: tổng hội thoại, số có tín hiệu vướng mắc, phân bố 3 nhóm (bảng dưới).
- **Mức độ khó theo chủ đề**: các cụm vướng mắc được gom tự động, xếp theo số hội thoại bị ảnh
  hưởng, tô nhãn mức độ 🔴/🟠/🟢 theo ngưỡng % công khai.
- **Hội thoại đáng xem trước**: top 5 theo điểm rủi ro — công thức cộng tuyến tính công bố ngay
  dưới bảng, kiểm lại được bằng tay.
- Nút **"▶ Phân tích bằng AI"**: AI đặt tên dễ hiểu cho từng cụm + viết lý do + gợi ý hành động
  cho giảng viên/TA. Kết quả lưu vào `results/khoi2_<ngày>.json` — mỗi ngày chỉ tốn đúng 1 lời
  gọi AI, F5 không mất.
- Ẩn danh tuyệt đối: chỉ hiện mã hội thoại, không hiện danh tính học viên; không xếp hạng cá nhân.

### 🗂️ Nhật ký hội thoại

- Đọc **nguyên văn từng hội thoại** học viên ↔ tutor (câu hỏi, trang/đoạn bôi đen, câu trả lời,
  nước đi sư phạm, rating 👍👎).
- Lọc theo ngày / nhóm vướng mắc / tìm theo mã hội thoại hoặc nội dung câu hỏi; bảng xếp theo
  điểm rủi ro, click 1 dòng để mở.
- Panel **phân tích hội thoại** bên phải: loại vướng mắc, mức độ, điểm rủi ro và từng tín hiệu
  chi tiết (lặp trang, hỏi lại cùng khái niệm, tự nói "không hiểu", rating cuối...).
- Nút **"⬇ Xuất hội thoại"** ra file .txt.
- Hội thoại demo live từ tab Chat cũng xem được tại đây (mục "🧪 Phiên demo hiện tại") — chứng
  minh pipeline chạy end-to-end với input mới.

## Cách hoạt động (pipeline)

```text
chatlog CSV ──> data_prep.py ──> signals.py ──────> classify_friction.py ──> app.py
 (1.261 cặp      ghép cặp         gắn tín hiệu        gom cụm (Python) +       hiển thị
  hỏi-đáp)       hỏi-đáp,         vướng mắc           AI đặt tên cụm, viết
                 group theo       rule-based          lý do & gợi ý hành động
                 ngày (giờ VN)    (không AI)          (lời gọi AI duy nhất)
transcript 6 buổi ──> transcript_index.py (index BM25, không embedding) ──┘
                          │
                          └──> agent_tutor.py (AI Tutor demo, ReAct/tool-calling)
file upload ──> upload_index.py (cùng khuôn dạng index) ──┘
```

Nguyên tắc xuyên suốt: **mọi con số là rule-based, đếm được, kiểm lại được** — AI chỉ làm việc
ngôn ngữ (đặt tên khái niệm, viết lý do, gợi ý hành động), không được đổi số liệu, không được
đổi nhãn phân loại.

### 3 nhóm vướng mắc (cài trong `signals.py`)

| Nhóm | Định nghĩa | Tín hiệu đếm được |
| --- | --- | --- |
| 🔧 Tutor Limitation | AI Tutor chưa hỗ trợ được | Câu trả lời chứa mẫu "không tìm thấy / rất tiếc / không thể truy cập..." |
| 📖 Learning Difficulty | Học viên có dấu hiệu chưa hiểu | Hỏi cùng 1 trang ≥3 lần · đổi diễn đạt hỏi lại · tutor phải cho đáp án trực tiếp · tự nói "không hiểu" · rating 👎 rồi rời đi |
| 💬 Learning Intent Drift | Không tập trung mục tiêu học | Chào hỏi/test · câu cụt · hỏi về chính con AI, thời tiết... |

Với nhóm Tutor Limitation, hệ thống tách tiếp **nguyên nhân gốc**: câu hỏi đối chiếu được với
transcript (≥50% từ khoá khớp) mà tutor vẫn fail → `retrieval_bug` (lỗi tìm kiếm, báo đội kỹ
thuật); ngược lại → `content_gap` (chưa dạy rõ trong 6 buổi được cấp, TA bổ sung tài liệu).

### Tìm kiếm tài liệu

`transcript_index.py` xếp hạng bằng **BM25** (tự cài, thuần Python, không embedding, không thêm
dependency) — từ hiếm/đặc trưng được ưu tiên hơn từ phổ biến. `match_ratio` (tỷ lệ từ khoá của
câu hỏi có mặt trong đoạn, thang 0–1) được giữ nguyên nghĩa để ngưỡng phân loại nguyên nhân gốc
và prompt của tutor không phải đổi.

## Cấu trúc thư mục

```text
app.py               -- ENTRY POINT: st.navigation sidebar 4 trang
app_pages/
  live_dashboard.py  -- 📡 KPI theo tuần/ngày, friction theo ngày, top vấn đề, khuyến nghị AI
  conversations.py   -- 💬 danh sách hội thoại (lọc tuần/ngày/nhóm/tìm kiếm) + transcript + phân tích
  reports.py         -- 📑 tổng hợp tuần, delta vs tuần trước, heatmap chủ đề × ngày, xuất báo cáo
  chat_tutor.py      -- 🎓 chat với AI Tutor (upload file riêng, nguồn trích dẫn)
ui_common.py         -- helper dùng chung: load data, gom TUẦN, báo cáo tuần, cache AI, điểm rủi ro
data_prep.py         -- đọc CSV chatlog, ghép cặp hỏi-đáp, group theo ngày (giờ VN)   [không AI]
transcript_index.py  -- index BM25 trên 700 đoạn transcript                           [không AI]
signals.py           -- gắn tín hiệu vướng mắc rule-based, 3 nhóm                     [không AI]
classify_friction.py -- gom cụm (Python) + AI đặt tên/lý do/gợi ý (LỜI GỌI AI CHÍNH)  [AI thật]
agent_tutor.py       -- AI Tutor demo, ReAct/tool-calling + GROUNDING GUARD chống bịa [AI thật]
upload_index.py      -- đọc PDF/PPTX/TXT/MD upload, chia trang/slide thành index      [không AI]
llm_client.py        -- client Groq dùng chung, đọc GROQ_API_KEY từ .env, tự retry    [hạ tầng]
dashboard.py         -- bản dashboard 1 file cũ, chạy độc lập (backup demo)
agent_demo_ui.py     -- bản chat tutor cũ, chạy độc lập (backup demo)
results/             -- cache kết quả AI phân tích theo ngày/tuần (gitignore)
.streamlit/          -- theme (2 chế độ sáng/tối, màu chủ đạo indigo)
```

## Chạy từng phần qua terminal (cho dev)

```bash
python3 data_prep.py                        # xem các ngày có data
python3 signals.py                          # breakdown 3 nhóm mỗi ngày (không cần API key)
python3 classify_friction.py 2026-07-27     # dry-run: in payload sẽ gửi AI, không tốn quota
python3 classify_friction.py 2026-07-27 --live   # gọi AI thật
python3 agent_tutor.py --live               # chat với tutor qua terminal
```

## Giới hạn & lưu ý kỹ thuật

- **Model Groq flaky**: `llama-3.3-70b-versatile` với tool-calling thỉnh thoảng sinh sai định
  dạng (`tool_use_failed`) — `llm_client.create_with_retry()` tự retry tối đa 3 lần.
- **Free tier 12.000 token/phút**: đây là lý do gom case thành cụm ở Python trước khi gửi AI
  (payload nhỏ, không phụ thuộc số case trong ngày) thay vì gửi toàn bộ case thô.
- **Gom cụm bằng từ khoá đại diện còn thô** (proxy "từ dài nhất") — có thể gom nhầm một số case;
  tên cụm sẽ chuẩn hơn sau khi AI đặt tên.
- Hội thoại demo live chỉ tồn tại trong phiên hiện tại, không ghi vào data pack thật.
- Data pack thuộc quy định bảo mật của khoá — không chia sẻ ra ngoài, không commit.

## Đã test live (2026-07-30)

- ✅ Phân tích AI (`classify_friction.py --live`): chạy thật trên ngày 22/07 (nhỏ) và 27/07
  (71 case → 25 cụm), phân biệt đúng `content_gap` vs `retrieval_bug`.
- ✅ AI Tutor (`agent_tutor.py --live`): câu hỏi chuẩn (trích dẫn đúng [T04-038]) · câu hỏi khó
  (thử 2 lần tra cứu rồi thành thật từ chối) · câu ngoài phạm vi (không gọi tool).
- ✅ App 3 tab: kiểm tra bằng `streamlit.testing.v1.AppTest` — không exception, kể cả kịch bản
  có phiên demo live.

## Việc còn thiếu

- [ ] Golden set ≥20 case trong `eval/` + 2 người chấm độc lập (xem `spec.md` §7)
- [ ] Click tay toàn bộ luồng trên trình duyệt thật trước demo
- [ ] Đánh giá chất lượng đặt tên cụm của AI trên nhiều ngày hơn
