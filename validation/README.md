# Validation — vòng user test (CP5)

**Người phụ trách:** Linh (kịch bản phỏng vấn + phỏng vấn), theo phân công chốt trong nhóm.
**Yêu cầu rubric R6 (8 điểm):** feedback log **≥5 mẩu từ ≥5 người ngoài nhóm** (trong đó ≥2
willing users đã khai từ CP1), **quote nguyên văn + tên/vai**; và **≥1 thay đổi từ feedback**
ghi vào `spec.md` §9 Changelog (hoặc giữ nguyên kèm lý do có căn cứ).

## Kịch bản test (10 phút/người)

1. Mở app (`streamlit run codebase/app.py`), đưa người test vào **tab Dashboard**, chọn ngày
   **2026-07-27** (ngày đông nhất), bấm "▶ Phân tích bằng AI" (hoặc dùng kết quả cache có sẵn).
2. Cho họ tự đọc 2 phút, không giải thích gì.
3. Bảo họ chat 3 câu ở **tab Chat** (1 câu về bài giảng, 1 câu mơ hồ, 1 câu ngoài phạm vi),
   rồi mở **tab Nhật ký** xem lại chính hội thoại vừa chat (mục "🧪 Phiên demo hiện tại").
4. Hỏi đúng 3 câu (đã chốt trong `spec.md` §8) và ghi **nguyên văn** câu trả lời:
   - **Q1.** "Nhìn bản đồ này, bạn quyết định dạy lại cái gì buổi sau?"
   - **Q2.** "Con số nào bạn không tin? Vì sao?"
   - **Q3.** "Có thông tin nào về học viên mà bạn thấy KHÔNG nên hiện không?"

## Ghi log

Mỗi người 1 mục trong `feedback-log.md` theo mẫu. Không sửa lời — ghi nguyên văn, kể cả chê.
Sau đủ ≥5 người: cả nhóm chọn ≥1 thay đổi từ feedback → làm → ghi Changelog `spec.md` §9
(trỏ về mã feedback, vd V03).
