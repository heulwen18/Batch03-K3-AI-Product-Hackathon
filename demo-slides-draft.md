# Nháp demo-slides (6 trang) — Linh dựng thành PDF

> Luật guide §5.1: **mỗi slide ≥1 con số / quote có nguồn / kết quả đo**. Tổng 5' trình bày +
> 5' Q&A, mỗi thành viên nói ≥1 phần. Mọi con số dưới đây đều tái tạo được bằng script trong
> `codebase/` và `eval/`.

## Slide 1 — User & Job *(45")* — gợi ý người nói: Mai Anh

- Job executor: **giảng viên/TA** khoá ~1.000 học viên.
- Core JTBD: *"Khi vừa dạy xong một buổi, tôi muốn biết cả lớp đang vướng ở khái niệm nào và
  vì sao, để buổi sau giảng lại đúng chỗ cần thay vì đoán."*
- Con số pain: **328/592 (55,4%)** hội thoại có tín hiệu vướng mắc — nhưng không ai đọc nổi
  **1.261 lượt chat** bằng tay.

## Slide 2 — Vì sao chọn tính năng này *(45")* — gợi ý: Phương

Bảng impact rút gọn (đầy đủ ở `spec.md` §2):

| Ứng viên | Số | Kết luận |
|---|---|---|
| Sửa retrieval tutor | 258/1.261 lượt fail (20,5%) | LOẠI — không có quyền sửa hệ thống VLearn; giữ làm insight bên trong |
| AI sinh quiz cuối buổi | không đo được từ data | LOẠI — thiếu evidence + cost-of-error cao |
| **Bản đồ Vướng Mắc Lớp** ✅ | 55,4% hội thoại vướng, 0 công cụ | CHỌN — 1 giảng viên dùng, ~1.000 HV hưởng |

## Slide 3 — Giải pháp & demo live *(2')* — gợi ý: Hoa Mai demo, Phương thuyết minh

- Lát cắt 1 câu: giảng viên/TA → cần biết lớp vướng gì → **AI đặt tên cụm vướng mắc (số liệu
  100% rule-based tính trước)** → Bản đồ Vướng Mắc: chủ đề × mức độ × gợi ý hành động.
- Automation: **augment** — AI đề xuất, người dạy quyết; sai tên cụm = vài giây đối chiếu quote,
  tự động hoá sai = hành động sai với cả lớp.
- **Demo live:**
  1. *Case chuẩn:* Dashboard ngày 27/07 → bấm Phân tích bằng AI → chỉ vào 1 cụm: tên + % + quote
     gốc + hành động → drill-down tab Nhật ký.
  2. *Case chỗ khó (①):* tab Chat hỏi "Giải thích Proof of Stake trong blockchain" → tutor
     **từ chối trung thực**, không bịa (GS11 trong golden set — pass).

## Slide 4 — Kết quả đo *(45")* — gợi ý: Phượng

- Quality bar (chốt 23:59 N1): **≥80% pass VÀ 0 case bịa nguồn (lớp ①)**.
- Golden set 22 case (8 chỗ khó + 10 thường + 4 hiếm; 13 từ chatlog thật), chấm tự động
  `eval/run_eval.py`:
  - Lượt 1: **16/17 = 94%** — 1 FAIL thật: GS15, regex meta quá hẹp miss câu "bạn là model ai
    nào vậy".
  - Sửa → Lượt 2 full (kèm 5 case AI live): **22/22 = 100% — ĐẠT bar**.
- Failure đáng kể nhất: chính GS15 — bài học "rule tưởng đúng cho tới khi có golden set".

## Slide 5 — User thật nói gì *(45")* — gợi ý: Linh

- *(điền sau vòng validation CP5 — lấy từ `validation/feedback-log.md`)*
- ≥2 quote nguyên văn + tên/vai; 1 thay đổi đã làm từ feedback (trỏ Changelog `spec.md` §9).

## Slide 6 — Nếu có thêm 1 tuần *(30")* — gợi ý: cả nhóm chốt

1. Embedding search đa ngữ thay BM25 — xử lý triệt để câu hỏi Việt/Anh lẫn (trỏ về nhóm case
   retrieval_bug = 50,8% lỗi tutor).
2. Đánh giá chất lượng đặt tên cụm trên nhiều ngày + mở rộng golden set ≥30 case (promptfoo).
3. Ghi hội thoại demo live vào pipeline hôm sau — khép kín vòng lặp dữ liệu.
- Bài học lớn nhất: *đo được thì mới cải thiện được — golden set bắt bug mà mắt thường bỏ qua.*

---

### Chuẩn bị Q&A (thẻ giám khảo — 3 câu bắt buộc trả lời được)

- **"Augment hay automate — vì sao?"** → augment; lý do cost-of-error ở Slide 3 / spec §4.
- **"Failure nguy hiểm nhất?"** → gắn nhầm "chưa hiểu bài" thành "lạc đề" → TA bỏ sót học viên
  (kịch bản #10, spec §5) — giảm rủi ro bằng thứ tự ưu tiên nhãn + hiện đủ mọi nhóm tín hiệu.
- **"Phần bạn làm?"** → mỗi người theo bảng phân công README.
- Backup demo: chụp màn hình/quay video 3 tab TRƯỚC buổi demo, phòng live hỏng (checklist 5.2).
