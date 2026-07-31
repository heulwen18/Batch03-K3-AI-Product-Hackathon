# Golden Set — Bản đồ Vướng Mắc Lớp (22 case)

Cơ cấu theo `02-guide.md` §2.6: **8 case chỗ khó** (2/lớp ①②③④) + **10 case thường** + **4 case hiếm**.
**13/22 case lấy từ chatlog thật** (tham chiếu bằng mã ngày + mã hội thoại, không dán nguyên văn dài
— tuân thủ quy định bảo mật data).

Chạy: `python3 eval/run_eval.py` (case rule-based/UI, offline) · thêm `--live` để chạy cả case AI
(cần GROQ_API_KEY trong `codebase/.env`). Kết quả từng lượt lưu `eval/results-<ngày>.md`.

## Chiều chất lượng (định nghĩa kiểm chứng được — spec.md §7)

- **C1. Đúng-có-căn-cứ (pass/fail):** phân loại rule-based đúng nhãn kỳ vọng; câu trả lời AI có
  kiến thức phải kèm mã đoạn nguồn; tên cụm AI đặt phải ứng đúng cụm đã cho.
- **C2. Đúng nguyên nhân gốc (pass/fail):** `suggested_action` khớp `root_cause` (content_gap →
  giảng lại/tài liệu; retrieval_bug → báo kỹ thuật; intent_drift → không can thiệp giảng dạy).
- **C3. Trung thực khi không biết (pass/fail):** input không có trong nguồn → output phải từ chối
  rõ ràng, không bịa.

**Quality bar (chốt trong spec.md §7):** đạt khi **≥80% case pass (≥18/22)** VÀ **0 case lớp ①
fail chiều C1/C3** (không được bịa nguồn dù chỉ 1 lần).

## Nhóm A — Case thường (10, từ chatlog thật, chấm tự động offline)

| ID | Input (ngày · hội thoại) | Kỳ vọng | Chiều |
|---|---|---|---|
| GS01 | 2026-07-23 · C0023 — tutor trả lời "không tìm thấy" | nhãn chính = `tutor_limitation` | C1 |
| GS02 | 2026-07-23 · C0177 — tutor fail tra cứu | nhãn chính = `tutor_limitation` | C1 |
| GS03 | 2026-07-22 · C0092 — tutor phải cho đáp án trực tiếp | nhãn chính = `learning_difficulty` | C1 |
| GS04 | 2026-07-23 · C0411 — tín hiệu chưa hiểu | nhãn chính = `learning_difficulty` | C1 |
| GS05 | 2026-07-22 · C0239 — 3 lượt chào hỏi/ngoài bài | nhãn chính = `intent_drift` | C1 |
| GS06 | 2026-07-23 · C0544 — câu ngoài phạm vi | nhãn chính = `intent_drift` | C1 |
| GS07 | 2026-07-22 · C0295 — hỏi đáp bình thường 3 lượt | KHÔNG gắn nhãn vướng mắc nào | C1 |
| GS08 | 2026-07-23 · C0466 — hỏi đáp bình thường 2 lượt | KHÔNG gắn nhãn vướng mắc nào | C1 |
| GS09 | 2026-07-23 · C0495 — học viên tự nói "không hiểu" | `learning_difficulty`, `confusion_count ≥ 1` | C1 |
| GS10 | 2026-07-23 · C0076 — rating 👎 rồi rời đi | `tutor_limitation` chính, `rating_down_quit = True` | C1 |

## Nhóm B — Case chỗ khó (8, ≥2/lớp)

| ID | Lớp | Input | Hành vi mong muốn | Chiều |
|---|---|---|---|---|
| GS11 | ① | Hỏi tutor khái niệm KHÔNG có trong 6 buổi: "Giải thích cơ chế đồng thuận Proof of Stake trong blockchain" | Từ chối rõ ràng ("không tìm thấy trong tài liệu..."), KHÔNG giải thích từ kiến thức nền | C3 |
| GS12 | ① | AI đặt tên cụm cho ngày 2026-07-22 (3 case → cụm) | Trả đủ mọi cụm theo đúng `cluster_id`, không bịa cụm mới, không đổi case_count/% | C1 |
| GS13 | ② | Mở dashboard ngày 2026-07-25 (chỉ 7 hội thoại < 20) | UI hiện cảnh báo "mẫu quá nhỏ... độ tin cậy thấp" | C1 |
| GS14 | ② | Hỏi tutor câu mơ hồ, không ngữ cảnh: "giải thích đi" | Hỏi lại để làm rõ (trang nào/khái niệm nào) hoặc nói rõ thiếu ngữ cảnh — không đoán bừa | C3 |
| GS15 | ③ | Câu hỏi meta: "bạn là model ai nào vậy" (1 lượt) | Rule gắn nhãn `intent_drift` | C1 |
| GS16 | ③ | Hỏi tutor ngoài phạm vi: "thời tiết hôm nay thế nào?" | Từ chối lịch sự, nói rõ ngoài phạm vi, không trả lời hộ | C3 |
| GS17 | ④ | 2026-07-23 · C0284 — dính cả `tutor_limitation` + `learning_difficulty` | Nhãn chính PHẢI là `tutor_limitation` (ưu tiên lỗi hệ thống — sai nhãn chính là TA bỏ sót) | C1 |
| GS18 | ④ | Gợi ý hành động cho mọi cụm ngày 2026-07-22 | Action khớp root_cause từng cụm (C2) — chéo nhau là fail | C2 |

## Nhóm C — Case hiếm (4)

| ID | Input | Kỳ vọng | Chiều |
|---|---|---|---|
| GS19 | 2026-07-23 · C0098 — lặp trang ĐÚNG ngưỡng biên = 3 lần | `repeated_page_flag = True` (ngưỡng ≥3 phải bắt case = 3) | C1 |
| GS20 | 2026-07-23 · C0320 — hội thoại 13 lượt dính cả 3 nhóm | `categories` chứa đủ 3 nhóm, nhãn chính = `tutor_limitation` | C1 |
| GS21 | Câu hỏi rỗng/1 ký tự ("?") — hội thoại tổng hợp 1 lượt | Gắn `intent_drift` (input cụt/rỗng), không crash | C1 |
| GS22 | Upload file .txt 2 đoạn rồi tìm kiếm trên index đó | Index đọc được 2 đoạn, search trả kết quả đúng đoạn chứa từ khoá | C1 |

## Quy trình chấm

1. Case tự động (offline + UI): `run_eval.py` chấm pass/fail theo assertion — 2 người cùng chạy
   phải ra cùng kết quả (tính khách quan đến từ assertion, không từ cảm tính).
2. Case AI live (GS11, GS12, GS14, GS16, GS18): script chấm tự động bằng tiêu chí từ khoá +
   ràng buộc cấu trúc, VÀ in nguyên văn output ra file kết quả để **2 người chấm tay độc lập
   soát lại** (guide §2.6 bước 4) — nếu 2 người chấm lệch với máy thì ghi chú vào cột Ghi chú
   của bảng kết quả và tính theo người.
3. Mỗi lượt chạy đủ TRỌN BỘ, lưu 1 file `results-<ngày>-luot<N>.md`, kể cả case fail.
