# Reflection — Phượng · [mã HV] · phần phụ trách: Kiểm thử + tối ưu

> Bản nháp có sẵn phần FACTS (việc đã làm, trỏ về file) — phần cảm nhận cá nhân (mục 2-5)
> tự viết bằng lời của mình trước khi nộp.

## 1. Tôi đã làm gì (cụ thể, trỏ về file/commit)

- Xây golden set 22 case (`eval/golden_set.md`): 8 case chỗ khó phủ 4 lớp ①②③④ + 10 case
  thường + 4 case hiếm; 13/22 case lấy từ chatlog thật (tham chiếu mã hội thoại, không dán
  nguyên văn dài để tuân thủ bảo mật data).
- Viết script chấm tự động `eval/run_eval.py`: case rule-based/UI chấm bằng assertion (ai chạy
  cũng ra cùng kết quả), case AI live chấm bằng tiêu chí từ khoá + ràng buộc cấu trúc và in
  nguyên văn output để chấm tay soát lại.
- Chạy trọn bộ 2 lượt, ghi kết quả trung thực (`eval/results-2026-07-30-luot*.md`):
  - Lượt 1 (offline): 16/17 = 94% — **GS15 FAIL**: câu "bạn là model ai nào vậy" không được
    gắn `intent_drift` vì regex `META_RE` quá hẹp.
  - Sửa `META_RE` trong `codebase/signals.py` (neo vào "bạn…" để không bắt nhầm câu hỏi bài
    học chính đáng) → lượt 2 full: **22/22 = 100%, đạt quality bar** (≥80% + 0 fail lớp ①).
- Tối ưu hệ thống: nâng retrieval lên BM25 (`transcript_index.py`, giữ nguyên nghĩa
  `match_ratio` cho downstream), thêm tín hiệu "tự nói không hiểu" (`CONFUSION_RE`), cache kết
  quả AI theo ngày (`codebase/results/`) để mỗi ngày chỉ tốn 1 lời gọi trên free tier.

## 2. Quyết định khó nhất tôi tham gia + vì sao chọn phương án đó

- *(gợi ý: chấm case AI bằng máy hay bằng người? — đã chọn máy chấm + in nguyên văn cho 2 người
  soát lại, vì sao?)*

## 3. Một thứ đã sai / suýt sai và tôi học được gì

- *(gợi ý: GS15 — rule tưởng đúng cho tới khi có golden set; bài học "look at your data"?)*

## 4. Nếu làm lại từ đầu, tôi đổi gì

- *(gợi ý: viết golden set TRƯỚC khi viết rule thay vì sau?)*

## 5. Kỹ năng AI product tôi mang về sau sự kiện

- …
