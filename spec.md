# AI SPEC — Bản đồ Vướng Mắc Lớp (Class Friction Map) · Nhóm K3 · Zone [X]

Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

> Prototype: `codebase/` (entry point `streamlit run app.py`). Mọi con số trong spec này
> tái tạo được bằng script trong `codebase/` — cách chạy ghi ở từng mục.

## §1. User & Job

- **Job executor + workflow:** Giảng viên/TA của khoá (~1.000 học viên). Workflow hiện tại sau
  mỗi buổi học: dạy xong → nhận cảm nhận rời rạc qua Discord/hỏi trực tiếp → đoán xem lớp có theo
  kịp không → soạn buổi sau dựa trên cảm giác. Không ai đọc lại chatlog tutor (1.261 lượt hỏi-đáp
  trong 9 ngày) vì quá nhiều và không có công cụ.
- **Core JTBD (không tên sản phẩm/AI):** *Khi vừa dạy xong một buổi, tôi muốn biết cả lớp đang
  vướng ở khái niệm nào và vì sao, để buổi sau tôi giảng lại đúng chỗ cần thay vì đoán.*
- **Problem statement (không chữ AI):** Giảng viên/TA không có cách nào nắm được lớp ~1.000 học
  viên đang kẹt ở đâu sau mỗi buổi học — dữ liệu hỏi-đáp có sẵn nhưng đọc tay 1.261 lượt là bất
  khả thi, dẫn tới chỗ học viên vướng nhiều nhất không được giảng lại, chỗ đã hiểu rồi lại bị
  nhắc lại.
- **Evidence (chuẩn B — mining data pack, phương pháp đếm kiểm lại được):**
  - **328/592 (55,4%)** hội thoại có ≥1 tín hiệu vướng mắc đếm được — cách đếm: ghép 1.261 cặp
    hỏi-đáp (`data_prep.py`), chạy `compute_conversation_signals()` trên từng hội thoại, đếm
    hội thoại có `friction_flag=True`. Chạy lại: `python3 codebase/signals.py`.
  - **258/1.261 (20,5%)** lượt tutor trả lời chứa mẫu câu thất bại ("không tìm thấy / rất tiếc /
    không thể truy cập...") — regex `FAIL_RE` trong `signals.py`.
  - **Con số mạnh nhất — 131/258 (50,8%)** lượt tutor "bó tay" nhưng nội dung học viên hỏi THẬT
    RA khớp ≥50% từ khoá với transcript 6 buổi được cấp → quá nửa lỗi tutor là lỗi tìm kiếm
    (`retrieval_bug`), không phải thiếu nội dung (`content_gap`). Đây là căn cứ tách nguyên nhân
    gốc trong sản phẩm.
  - **582/1.261 (46,2%)** lượt tutor không ghi nguồn (citations rỗng) — lọc `role=tutor`, đếm
    bản ghi `citations=[]`.
  - **47/592 (7,9%)** hội thoại có học viên hỏi đi hỏi lại cùng 1 trang ≥3 lần; rating 👎 (37)
    nhiều hơn 👍 (33) trên các lượt có đánh giá.
  - **≥5 ví dụ nguyên văn** (mã lượt hỏi trong chatlog, đã ẩn danh sẵn):
    1. `[T0399]` HV: *"Giải thích biều đồ đc bôi đỏ"* → tutor: *"Rất tiếc, tôi đã thực hiện tra cứu trong các slide bài giảng nhưng hiện tại khôn[g tìm thấy]..."*
    2. `[T0578]` HV: *"tóm tắt slide"* → tutor: *"rất tiếc là mình hiện chưa tra cứu được nội dung chi tiết từ slide..."*
    3. `[T1100]` HV: *"Tui không hiểu"* — tự nói bối rối, tín hiệu Learning Difficulty trực tiếp.
    4. `[T0638]` HV: *"chào bạn, mình chưa hiểu về RAG"*
    5. `[T0525]` HV: *"là sao fen tôi chưa hiểu lắm, định nghĩa lại feature extraction giúp tôi"*
    6. `[T1096]` HV: *"giải thích cho tôi toàn bộ slide trong này đi"* → rating 👎.

## §2. Impact & quyết định chọn

| Ứng viên | Bao nhiêu người | Tần suất | Tốn gì mỗi lần | Khả thi trong sự kiện |
|---|---|---|---|---|
| (a) Sửa retrieval của tutor hiện có | ~1.000 HV | 20,5% lượt hỏi bị fail (258/1.261) | HV mất câu trả lời, mất niềm tin | ✗ Không có quyền can thiệp hệ thống VLearn thật |
| (b) AI sinh quiz kiểm tra hiểu cuối buổi | ~1.000 HV | 1 lần/buổi | Không đo được từ data được cấp | ✗ Thiếu evidence chuẩn B; AI sinh câu hỏi/đáp án sai → học sai ngay |
| (c) **Bản đồ Vướng Mắc Lớp cho giảng viên/TA** ✅ | Trực tiếp: đội giảng viên/TA; gián tiếp ~1.000 HV | Sau mỗi buổi học | Hiện tại: không làm được (đọc tay 1.261 lượt) → dạy lại theo cảm giác | ✓ Data đủ, số liệu làm được 100% rule-based, AI chỉ 1 quyết định gọn |

- **Ứng viên ĐÃ LOẠI + vì sao:** (a) evidence mạnh nhất (20,5% fail, 50,8% trong đó là retrieval
  bug) nhưng là sửa hệ thống của người khác — không demo end-to-end được trong sự kiện; giữ lại
  làm **insight bên trong** ứng viên (c): dashboard tách `retrieval_bug` để báo đội kỹ thuật.
  (b) không có bằng chứng pain từ data được cấp + cost-of-error cao nhất trong 3 ứng viên.
- **Ứng viên CHỌN + vì sao (bằng số):** (c) — 55,4% hội thoại có tín hiệu vướng mắc mà không ai
  đọc; 1 người dùng (giảng viên) nhưng tác động lan tới ~1.000 học viên mỗi buổi; phần rủi ro
  (con số) làm bằng rule-based kiểm lại được, AI chỉ đặt tên + gợi ý nên sai cũng không phá số liệu.

## §3. Giải pháp tương tự đã nghiên cứu

- **Khanmigo Teacher Tools (Khan Academy):** dashboard cho giáo viên xem học sinh tương tác với
  tutor AI. *Đáng học:* tổng hợp cấp lớp trước, drill-down sau. *Đáng né:* hiển thị theo dõi từng
  học sinh — dễ thành công cụ giám sát. *Mình khác:* ẩn danh tuyệt đối, chỉ tổng hợp cấp lớp,
  điểm rủi ro là của hội thoại chứ không phải của học viên.
- **Intercom/Chatbase conversation topics:** gom hội thoại CSKH thành chủ đề bằng AI. *Đáng học:*
  gom cụm trước rồi mới đặt tên. *Đáng né:* AI tự tính cả % và volume — không kiểm lại được.
  *Mình khác:* mọi con số do Python đếm, AI chỉ được đặt tên cụm (kiến trúc "AI không đổi số liệu").

## §4. Thiết kế

- **Lát cắt MỘT CÂU:** Một **giảng viên/TA**, sau mỗi buổi học cần **biết lớp đang vướng khái
  niệm nào và nên làm gì**, hệ thống để **AI đặt tên các cụm vướng mắc (đã được gom và tính số
  bằng rule-based) + viết gợi ý hành động theo nguyên nhân gốc**, trả về **"Bản đồ Vướng Mắc Lớp"
  của ngày đó: chủ đề × mức độ × hành động, drill-down được về hội thoại gốc ẩn danh**.
- **Non-goals (≥3):**
  1. KHÔNG hiển thị danh tính/`user_id` học viên, KHÔNG xếp hạng hay gắn nhãn học viên cá nhân.
  2. KHÔNG tự sinh nội dung dạy lại — chỉ chỉ ra vướng ở đâu, vì sao, gợi ý 1 câu hành động.
  3. KHÔNG cho AI tính/thay đổi số liệu (case_count, %, nhãn phân loại) — số là của Python.
  4. KHÔNG OCR slide dạng ảnh scan; KHÔNG lưu hội thoại demo vào data pack thật.
- **Mức prototype:** [x] Working — chạy end-to-end với data pack thật. Phần **thật**: toàn bộ
  pipeline đếm + gom cụm + lời gọi AI đặt tên (`classify_friction.py`) + dashboard + nhật ký hội
  thoại + AI Tutor demo (ReAct/tool-calling, sinh hội thoại sống nối vào đúng pipeline). Phần
  **mock/không có**: không có hệ thống rating/move sư phạm cho tutor demo (các field này để trống,
  không suy diễn).
- **Automation:** [x] augment. Lý do theo cost-of-error: nếu AI đặt tên cụm sai/gợi ý sai, giảng
  viên nhìn quote nguyên văn + số liệu rule-based bên cạnh là phát hiện được ngay (chi phí sai =
  vài giây đối chiếu); nhưng nếu hệ thống tự động ra quyết định (ví dụ tự gửi thông báo "lớp yếu
  phần X" hay tự xếp lịch dạy lại) thì một lần phân loại nhầm sẽ thành hành động sai với cả lớp.
  Vì vậy AI chỉ đề xuất, người dạy quyết định.

### §4b. Nguyên tắc đã áp dụng (HAX/PAIR)

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| **G1 — Làm rõ làm được gì** | Câu chào đầu tiên của tutor liệt kê đúng 3 việc: hỏi trên 6 buổi giảng, upload file riêng, nhập trang mô phỏng bôi đen (`app.py` render_chat_tab). Dashboard ghi rõ phần nào rule-based, phần nào AI. |
| **G2 — Làm rõ tốt đến đâu** | Cảnh báo mẫu nhỏ khi ngày < 20 hội thoại; `low_confidence_note` khi cụm < 3 case; cột "Mức độ" dùng ngưỡng % công khai (SEVERITY_HIGH/MED trong `app.py`), không phải điểm AI chấm. |
| **G10 — Thu hẹp phạm vi khi nghi ngờ** | Tutor không đủ căn cứ (match thấp) → trả lời "mình không tìm thấy trong 6 buổi được cấp — bạn nên hỏi giảng viên/TA", tuyệt đối không bịa (system prompt `agent_tutor.py`). AI đặt tên bị ràng buộc "không thêm cụm, không bỏ cụm, không đổi số" (SYSTEM_PROMPT `classify_friction.py`). |
| **G11 — Giải thích vì sao** | Mỗi khái niệm trên dashboard có `cause_rationale` + quote nguyên văn + mã đoạn transcript; mỗi câu trả lời tutor có "📚 Nguồn đã tra cứu" (mã đoạn, % khớp, trích đoạn gốc). |
| **PAIR — Explainability & Trust (tin đúng mức)** | Công thức điểm rủi ro in ngay dưới bảng, cộng tuyến tính kiểm được bằng tay; tab Nhật ký cho drill-down về nguyên văn từng hội thoại để tự kiểm mọi kết luận. |
| **G8/G9 — Gạt bỏ/sửa dễ dàng** | Kết quả AI chỉ là 1 khối bổ sung — không bấm "Phân tích bằng AI" thì dashboard vẫn đầy đủ số liệu; chat có "🔄 Hội thoại mới" và hỏi lại được ngay. |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

| # | Tình huống cụ thể | Lớp | Hành vi mong muốn | Nguyên tắc |
|---|---|---|---|---|
| 1 | AI đặt tên cụm tự "sáng tác" số liệu (%/case_count) | ① | Số do Python tính sẵn, AI chỉ nhận danh sách cụm đã có số — schema tool ép trả đúng `cluster_id` | G10 |
| 2 | AI kết luận "giảng viên chưa dạy X" trong khi chỉ là không có trong 6 buổi được cấp | ① | Rationale bắt buộc viết "trong 6 buổi được cấp, có thể đã dạy buổi khác" — không khẳng định tuyệt đối | G2, G11 |
| 3 | Tutor demo bịa câu trả lời từ kiến thức nền khi transcript không có (kể cả bịa mã trích dẫn) | ① | HAI lớp bảo vệ: prompt cấm + **grounding guard rule-based** (có tra cứu mà best match < 0.5 → buộc từ chối). Guard thêm sau khi golden set lượt 4 bắt được model vượt prompt (bịa mã T04-006) | G10 |
| 4 | Ngày chỉ có 5–11 hội thoại, % không đáng tin | ② | Tự hiện cảnh báo "mẫu quá nhỏ (< 20), độ tin cậy thấp" — vẫn hiện số, không giấu | G2 |
| 5 | Cụm chỉ 1–2 case được đặt tên nghe như xu hướng cả lớp | ② | Model phải trả `low_confidence_note`; bảng luôn hiện case_count bên cạnh tên | G2 |
| 6 | Học viên hỏi cụt ("PRD?", "giải thích đi") không đủ ngữ cảnh | ② | Tutor hỏi lại 1 câu để làm rõ thay vì đoán | G10 |
| 7 | Giảng viên muốn xem đích danh học viên "yếu" để nhắc nhở | ③ | Chỉ hiện mã hội thoại ẩn danh; điểm rủi ro là CỦA HỘI THOẠI — non-goal ghi ngay trong caption | G1 |
| 8 | Học viên đòi tutor cho đáp án quiz/bài tập, hoặc hỏi ngoài bài ("bạn là model gì", thời tiết) | ③ | Từ chối lịch sự, nói rõ ngoài phạm vi, không gọi tool | G1, G10 |
| 9 | Tutor giải thích sai khái niệm nhưng văn trôi chảy → học viên học sai | ④ | Mọi câu trả lời kèm mã đoạn trích dẫn + panel nguồn để kiểm; không có nguồn thì phải nói không tìm thấy | G11 |
| 10 | Hội thoại "chưa hiểu bài" bị gắn nhầm thành "chào hỏi lạc đề" → TA bỏ sót học viên cần giúp | ④ | Ưu tiên nhãn theo thứ tự tutor_limitation > learning_difficulty > intent_drift; tab Nhật ký hiện đủ MỌI nhóm tín hiệu (không chỉ nhóm chính) để người xem tự soát | G9, PAIR |

*(Kịch bản nhóm sợ nhất khi demo: #10 — sai âm thầm mà nhìn vẫn "đúng".)*

## §6. Bốn đường đi của trải nghiệm

- **Happy path:** chọn ngày → thấy ngay tổng quan + phân bố 3 nhóm + heatmap chủ đề (rule-based,
  không cần chờ AI) → bấm "▶ Phân tích bằng AI" → nhận tên khái niệm dễ đọc + gợi ý hành động →
  mở Conversation Explorer xem quote gốc.
- **Low-confidence (②):** ngày < 20 hội thoại → banner cảnh báo mẫu nhỏ ngay trên số liệu; cụm
  < 3 case → `low_confidence_note` hiện thành warning riêng. Số vẫn hiện, nhãn tin cậy đi kèm.
- **Failure/không căn cứ (①):** tutor không tìm thấy → nói thẳng "không tìm thấy trong 6 buổi
  được cấp" + hướng sang giảng viên/TA; AI phân tích lỗi (API/model) → thông báo lỗi rõ + dashboard
  rule-based vẫn nguyên vẹn, không mất gì.
- **Correction (user sửa):** học viên hỏi lại/diễn đạt lại ngay trong chat (lịch sử giữ nguyên);
  giảng viên nghi ngờ kết quả AI → đối chiếu quote nguyên văn + mở tab Nhật ký đọc hội thoại gốc;
  muốn chạy lại → bấm "▶ Phân tích bằng AI" lần nữa (kết quả mới ghi đè cache).
- **Khi bị đòi ngoài phạm vi (③):** xem kịch bản #7, #8 — từ chối + nói rõ giới hạn, vẫn chỉ
  đường đi tiếp hữu ích.
- **Case đặc thù domain (④):** xem kịch bản #9, #10 — trích dẫn bắt buộc + hiển thị đủ mọi nhóm
  tín hiệu để con người soát lại được.

## §7. Kiểm thử

- **Chiều chất lượng + định nghĩa kiểm chứng được:**
  1. *Đúng-có-căn-cứ (pass/fail):* mọi tên khái niệm AI đặt phải trỏ về được ≥1 quote trong cụm;
     mọi câu trả lời tutor có nội dung kiến thức phải kèm ≥1 mã đoạn nguồn. Fail nếu có claim
     không trace được.
  2. *Đúng nguyên nhân gốc (pass/fail):* `suggested_action` phải khớp `root_cause` đã cho
     (content_gap → giảng lại/bổ sung tài liệu; retrieval_bug → báo kỹ thuật; intent_drift →
     không can thiệp giảng dạy). Fail nếu chéo nhau.
  3. *Trung thực khi không biết (pass/fail):* input không có trong nguồn → output phải chứa từ
     chối rõ ràng, không chứa nội dung bịa.
- **Golden set (22 case, file `eval/golden_set.md`, chạy bằng `eval/run_eval.py`):** cơ cấu theo
  guide §2.6 — 8 case chỗ khó (2/lớp ①②③④) + 10 case thường + 4 case hiếm; **13/22 case từ chatlog
  thật** (tham chiếu bằng mã ngày + mã hội thoại). Case rule-based/UI chấm tự động bằng assertion
  (2 người chạy ra cùng kết quả); case AI live chấm bằng tiêu chí từ khoá + ràng buộc cấu trúc,
  nguyên văn output được in vào file kết quả để 2 người chấm tay soát lại.
- **Quality bar (chốt từ 23:59 N1, giữ nguyên):** *"Đạt khi ≥80% case qua cả 3 chiều, VÀ điều kiện
  cứng: 0 case bịa nguồn (chiều 1 và 3 không được fail ở bất kỳ case lớp ① nào)."*
- **Kết quả các lượt chạy:** *(file chi tiết trong `eval/results-*.md`, kể cả case fail)*

  | Lượt | Thời điểm | Số case pass/tổng | % | Ghi chú |
  |---|---|---|---|---|
  | Smoke test tay | 2026-07-30 | 5/5 | — | 3 kịch bản tutor + 2 ngày phân tích AI — chưa phải lượt golden set chính thức |
  | Lượt 1 (offline) | 2026-07-30 | 16/17 | 94% | **GS15 FAIL** — "bạn là model ai nào vậy" không được gắn intent_drift (regex META quá hẹp, dạng câu có thật trong chatlog). 5 case AI skip |
  | Lượt 2 (full, sau khi sửa META_RE) | 2026-07-30 | 22/22 | 100% | **ĐẠT quality bar** — lớp ① sạch |
  | Lượt 3 (offline, sau khi refactor UI 4 trang) | 2026-07-31 | 17/17 | 100% | Xác nhận refactor không phá rule-based/UI; case AI skip |
  | Lượt 4 (full) | 2026-07-31 | 21/22 | 95% | **GS11 FAIL — CHƯA ĐẠT bar** (vi phạm điều kiện cứng lớp ①): tutor tự giải thích "Proof of Stake" từ kiến thức nền + **bịa mã trích dẫn T04-006** dù best match chỉ 25-33% — model flaky, prompt đơn thuần không đủ chặn |
  | Lượt 5 (full, sau khi thêm grounding guard) | 2026-07-31 | 22/22 | 100% | **ĐẠT quality bar** — guard rule-based trong `agent_tutor.py`: có tra cứu mà best match < 0.5 → buộc từ chối trung thực; đã kiểm chứng không chặn nhầm câu hỏi hợp lệ (best match 1.0 vẫn trả lời bình thường) |

## §8. Phân công & kế hoạch

- **Phân công có tên** :
  - **Mai Anh** — evidence/mining: xử lý dữ liệu có sẵn, phân tích chatlog
  - **Hoa Mai** — frontend: giao diện Streamlit + deploy
  - **Phương** — code: build pipeline phân loại, tích hợp các phần
  - **Linh** — demo: slide + kịch bản phỏng vấn validation + phỏng vấn user
  - **Phượng** — kiểm thử: golden set + `eval/run_eval.py` + tối ưu (BM25, cache, tín hiệu)
  - spec: cả nhóm góp, chốt chung trước 23:59 N1
- **Willing users (≥3 tên):** [Tên 1 — Lab Coach], [Tên 2 — giảng viên], [Tên 3 — học viên zone khác]
  *(nhóm điền từ CP1 — Linh phụ trách chốt danh sách)*. **Kế hoạch validation CP5:** cho ≥5 người ngoài nhóm dùng dashboard với
  ngày 27/07 + tự chat 3 câu rồi xem tab Nhật ký; 3 câu hỏi: (1) "Nhìn bản đồ này, bạn quyết định
  dạy lại cái gì buổi sau?" (2) "Con số nào bạn không tin? Vì sao?" (3) "Có thông tin nào về học
  viên mà bạn thấy KHÔNG nên hiện không?"; [Tên] log nguyên văn vào `validation/`.
- **Multi-prototype:** trục khác biệt đã cân nhắc = *dạng output của quyết định AI*: (A) AI đọc
  toàn bộ case thô và tự viết báo cáo tự do vs (B) Python gom cụm + tính số trước, AI chỉ đặt tên
  (đã chọn). Chọn (B) vì: free tier 12.000 token/phút không chứa nổi payload ngày đông (~37.000
  token); và (A) không kiểm lại được số liệu — vi phạm nguyên tắc xương sống.

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| 2026-07-28 | Chuyển phân loại sang kiến trúc "Python gom cụm + AI chỉ đặt tên" | Payload ngày 27/07 (71 case, ~37K token) vượt giới hạn 12K token/phút của Groq free tier |
| 2026-07-29 | Gộp 2 web thành 1 app duy nhất (`app.py`), sửa KeyError 'cases' | Demo 2 màn hình rời gây rối; bug phát hiện khi chạy thử |
| 2026-07-30 | Thêm tab Nhật ký hội thoại + panel phân tích từng hội thoại; bỏ sidebar cấu hình | Yêu cầu xem được nguyên văn hội thoại + phân tích tại chỗ; ô nhập API key trên UI dễ lộ khoá khi demo/chụp màn hình |
| 2026-07-30 | Retrieval nâng lên BM25; thêm tín hiệu "tự nói không hiểu"; cache kết quả AI theo ngày; biểu đồ xu hướng; panel nguồn trích dẫn | Keyword-overlap thô xếp hạng kém; tiết kiệm quota (mỗi ngày 1 lời gọi); tăng khả năng tự kiểm chứng (G11) |
| 2026-07-30 | Bỏ chế độ dry-run khỏi UI (giữ ở CLI cho dev) | Người dùng thật (giảng viên) không cần khái niệm dry-run — giảm 1 quyết định thừa trên giao diện |
| 2026-07-30 | Mở rộng `META_RE` trong `signals.py` (bắt "bạn là model ai nào", "bạn dùng model llm gì") | Golden set lượt 1 case GS15 FAIL — regex cũ quá hẹp, miss dạng câu meta có thật trong chatlog; sửa xong chạy lại trọn bộ 22/22 pass |
| 2026-07-31 | Tái cấu trúc UI thành 4 trang sidebar (Live Dashboard / Conversations / Reports / Chat) + gom dữ liệu theo TUẦN, không giới hạn số buổi; bỏ chú thích phương pháp khỏi mặt giao diện (chuyển thành tooltip); mọi insight hiện kèm số hội thoại gốc | Feedback validation V01-V05: 4/5 muốn số hội thoại gốc đi kèm insight (P0), 3/5 muốn giải thích cách tính chỉ số (→ tooltip), 2/5 thấy giao diện nhiều chữ; mockup UI nhóm chốt |
| 2026-07-31 | Thêm grounding guard vào `agent_tutor.py` (best match < 0.5 → buộc từ chối) | Golden set lượt 4 case GS11 FAIL — model vượt prompt, tự giải thích "Proof of Stake" + bịa mã trích dẫn; lượt 5 chạy lại 22/22 ĐẠT |
