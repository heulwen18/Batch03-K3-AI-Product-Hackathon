# Codebase — Bản đồ Vướng Mắc Lớp (Class Friction Map / "AI Learning Analytics Copilot")

Tương ứng lát cắt trong `spec.md` §4. Trạng thái hiện tại: **Khối 1 + Khối 2 + Khối 3 + Agent A xong**.

## Kiến trúc

```
llm_client.py         -- client Groq dùng chung, đọc GROQ_API_KEY từ .env tự động   [KHÔNG AI —
                         (python-dotenv), retry khi model sinh sai định dạng           hạ tầng]
                         tool-call (flaky, đã quan sát thực tế)
data_prep.py         -- đọc CSV chatlog, ghép turn, group theo ngày (giờ VN)         [KHÔNG AI]
transcript_index.py  -- index keyword-overlap trên 700 đoạn transcript              [KHÔNG AI]
signals.py           -- KHỐI 1: rule-based, phân loại 3 nhóm friction (canvas CP1):  [KHÔNG AI]
                         tutor_limitation / learning_difficulty / intent_drift
classify_friction.py -- KHỐI 2: LỜI GỌI AI THẬT (Groq) — Python gom case thành cụm   [AI THẬT]
                         + tính case_count/percent/root_cause chính xác trước; model
                         chỉ đặt tên khái niệm + viết rationale/suggested_action.
                         Ép JSON bằng tool-calling (function calling).
dashboard.py          -- KHỐI 3: UI Streamlit cho giảng viên — breakdown 3 nhóm      [KHÔNG AI —
                         (Khối 1, tức thời) + bấm nút mới chạy Khối 2 (dry-run mặc      chỉ điều
                         định để không tốn quota)                                      phối hiển
                                                                                        thị]
agent_tutor.py        -- AGENT A: chatbot demo ReAct/tool-calling (Groq, KHÔNG phải [AI THẬT —
                         tính năng được chấm) — mô phỏng VLearn tutor cho học viên     nhưng chỉ
                         chat live, tool search_transcript, tối đa 2 vòng tool/câu     để DEMO]
                         hỏi
agent_demo_ui.py       -- UI Streamlit cho Agent A (màn hình phụ demo Nhịp 2) — chat
                         live rồi nối thẳng vào Khối 1+2 để phân loại ngay
```

**Quan trọng:** Agent A không phải "quyết định AI trung tâm" được chấm — nó chỉ sinh input sống cho demo. Quyết định được chấm vẫn là Khối 2 (`classify_friction.py`).

## Cách chạy thử

```bash
pip install -r requirements.txt

# Đặt API key trong codebase/.env (đã có sẵn, KHÔNG commit — nằm trong .gitignore):
#   GROQ_API_KEY = gsk_...

# Xem các ngày có data
python3 data_prep.py

# Khối 1 riêng — breakdown 3 nhóm mỗi ngày (không cần API key)
python3 signals.py

# Khối 2 — mặc định DRY RUN (không gọi API, chỉ in payload sẽ gửi để kiểm tra trước khi tốn quota)
python3 classify_friction.py 2026-07-27

# Khối 2 — gọi AI THẬT (đọc GROQ_API_KEY từ .env tự động, không cần export)
python3 classify_friction.py 2026-07-27 --live

# Agent A — test nhanh qua terminal
python3 agent_tutor.py --live

# Khối 3 — dashboard giảng viên
streamlit run dashboard.py

# Agent A — demo chat live (chạy port khác để mở song song lúc demo)
streamlit run agent_demo_ui.py --server.port 8502
```

**Lưu ý model Groq flaky:** `llama-3.3-70b-versatile` với `tool_choice="auto"` thỉnh thoảng sinh sai định dạng function-call (lỗi `tool_use_failed`) — đã quan sát thực tế là không nhất quán (cùng prompt lúc được lúc không). `llm_client.create_with_retry()` tự retry tối đa 3 lần, đủ xử lý trong thực tế.

**Giới hạn free tier:** 12.000 token/phút — đây là lý do Khối 2 gom case thành cụm ở Python trước khi gửi AI (xem docstring đầu `classify_friction.py`), thay vì gửi thẳng toàn bộ case thô.

## 3 nhóm friction (đã cài trong `signals.py`)

| Nhóm | Định nghĩa | Ví dụ |
|---|---|---|
| 🔧 Tutor Limitation | AI Tutor chưa hỗ trợ được (không tìm thấy tài liệu / trả lời chưa đúng câu hỏi) | *"Xin lỗi, tôi không tìm thấy nội dung cụ thể cho slide này..."* |
| 📖 Learning Difficulty | Học viên có dấu hiệu chưa hiểu (hỏi lại cùng khái niệm / cần giải thích nhiều lần / hiểu nhầm) | Hỏi liên tục "Context là gì?", "Context có phải Memory không?" |
| 💬 Learning Intent Drift | Không tập trung vào mục tiêu học (câu hỏi ngoài phạm vi / chào hỏi / tương tác không liên quan) | "Hello", "Bạn là model nào?" |

Category do Khối 1 (rule-based) gắn cố định cho mỗi case — Khối 2 (AI) **không được** tự đổi, chỉ gom theo khái niệm + tinh chỉnh nguyên nhân bên trong nhóm Tutor Limitation (`content_gap` vs `retrieval_bug`). Xem thêm `spec.md` §4-§6.

## ⚠️ Bài học rút ra — commit sớm

Toàn bộ thư mục `codebase/` từng bị MẤT một lần do thao tác `git checkout`/`reset` giữa các branch trong lúc file vẫn ở trạng thái untracked (chưa commit). Đã khôi phục lại từ lịch sử làm việc. **Khuyến nghị: commit `codebase/` vào git ngay sau khi đọc xong README này**, tránh lặp lại sự cố khi có thao tác git khác trong nhóm.

## Đã test live (2026-07-30)

- ✅ Khối 2 (`classify_friction.py --live`): chạy thật trên ngày 22/07 (nhỏ) và 27/07 (71 case → 25 cụm), phân biệt đúng `content_gap` vs `retrieval_bug`.
- ✅ Agent A (`agent_tutor.py --live`): 3 kịch bản test qua terminal — câu hỏi chuẩn (trích dẫn đúng [T04-038]), câu hỏi "ReAct" (thử 2 tool call, thành thật từ chối đúng kịch bản ① trong spec.md), câu hỏi ngoài phạm vi (không gọi tool).

## Việc còn thiếu để chạy end-to-end (đưa vào eval/ + golden set)

- [ ] Trích ≥20 case cho golden set từ output Khối 1 (đã có sẵn cấu trúc `friction_cases`) + 2 người chấm độc lập so kết quả
- [ ] Test `dashboard.py` và `agent_demo_ui.py` qua trình duyệt thật (mới test boot sạch, chưa click tay toàn bộ luồng)
- [ ] Nhóm tự đánh giá chất lượng đặt tên khái niệm của Khối 2 trên nhiều ngày hơn — proxy "từ dài nhất" để gom cụm còn thô, có thể gom nhầm 1 số case (vd cụm tên "thich" ở ngày 27/07)
