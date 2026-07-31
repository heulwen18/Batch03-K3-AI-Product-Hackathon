# Reflection — Phượng · [mã HV] · phần phụ trách: Kiểm thử + tối ưu

## 1. Tôi đã làm gì (cụ thể, trỏ về file/commit)

- Xây golden set 22 case (`eval/golden_set.md`): 8 case chỗ khó phủ 4 lớp ①②③④ + 10 case
  thường + 4 case hiếm; 13/22 case lấy từ chatlog thật (tham chiếu mã hội thoại, không dán
  nguyên văn dài để tuân thủ bảo mật data).
- Viết script chấm tự động `eval/run_eval.py`: case rule-based/UI chấm bằng assertion (ai chạy
  cũng ra cùng kết quả), case AI live chấm bằng tiêu chí từ khoá + ràng buộc cấu trúc và in
  nguyên văn output để chấm tay soát lại.
- Chạy trọn bộ 5 lượt, ghi kết quả trung thực (`eval/results-*.md`, kể cả lượt fail):
  - Lượt 1 (offline): 16/17 = 94% — **GS15 FAIL**: câu "bạn là model ai nào vậy" không được
    gắn `intent_drift` vì regex `META_RE` quá hẹp → sửa → lượt 2 full 22/22 ĐẠT.
  - Lượt 4 (sau refactor UI): **GS11 FAIL nghiêm trọng** — tutor tự giải thích "Proof of Stake"
    từ kiến thức nền + bịa mã trích dẫn T04-006 → thêm grounding guard → lượt 5 22/22 ĐẠT.
- Tối ưu hệ thống: nâng retrieval lên BM25 (`transcript_index.py`, giữ nguyên nghĩa
  `match_ratio` cho downstream), thêm tín hiệu "tự nói không hiểu" (`CONFUSION_RE`), grounding
  guard chống bịa trong `agent_tutor.py`, cache kết quả AI theo ngày/tuần (`codebase/results/`),
  fallback model khi hết quota ngày (`llm_client.py`).

## 2. Quyết định khó nhất tôi tham gia + vì sao chọn phương án đó

Quyết định khó nhất của tôi là **chấm case AI bằng máy hay bằng người**. Case rule-based thì dễ
— assertion là xong, ai chạy cũng ra một kết quả. Nhưng case AI (tutor có từ chối trung thực
không, gợi ý hành động có khớp nguyên nhân gốc không) thì output là văn tự do: chấm bằng người
thì chủ quan và không lặp lại được, chấm bằng máy thì tiêu chí từ khoá có thể chấm sai (câu từ
chối viết kiểu khác là máy bắt hụt). Tôi chọn phương án lai: **máy chấm bằng tiêu chí từ khoá +
ràng buộc cấu trúc trước, nhưng in nguyên văn output vào file kết quả để hai người chấm tay
độc lập soát lại** — nếu người và máy lệch nhau thì tính theo người và ghi chú lại. Lý do: nhịp
lặp "sửa → chạy lại trọn bộ" phải đủ nhanh (máy chấm 22 case trong ~1 phút), nhưng độ tin cuối
cùng phải là của con người. Thực tế phương án này đã tự chứng minh: chính tiêu chí từ khoá của
máy bắt được vụ GS11 bịa trích dẫn mà nếu chấm tay theo cảm tính rất dễ cho qua, vì câu trả lời
đọc rất trôi chảy và "có vẻ đúng".

Một quyết định khó thứ hai là **ngưỡng grounding guard đặt bao nhiêu**. Tôi không chọn theo cảm
tính mà đo trên query thật: câu bịa được ("Proof of Stake") có best match 0,25–0,33; câu trả lời
được đều ≥ 0,67. Chọn 0,5 — trùng luôn với `RETRIEVAL_BUG_THRESHOLD` đang dùng ở tầng phân loại,
nên hệ thống chỉ có một khái niệm "đủ căn cứ" duy nhất, dễ giải thích khi bị hỏi.

## 3. Một thứ đã sai / suýt sai và tôi học được gì

Cái sai đáng nhớ nhất không phải GS15 mà là **GS11 lượt 4**. Cùng một case đó lượt 2 đã PASS —
tutor từ chối trung thực đúng kịch bản. Hai ngày sau chạy lại, model lại tự tin giải thích Proof
of Stake từ kiến thức nền và **bịa luôn mã trích dẫn T04-006** cho ra vẻ có nguồn, trong khi độ
khớp tra cứu thật chỉ 25–33%. Nếu golden set chỉ chạy một lần rồi cất đi, chúng tôi đã mang một
con tutor "thỉnh thoảng bịa nguồn" đi demo mà không biết — và đây đúng là kịch bản nhóm khai
trong spec là "sợ nhất" (lớp ① — sai mà trông đáng tin).

Tôi học được hai điều. Một: **prompt không phải là cơ chế an toàn** — prompt đã cấm rõ ràng mà
model vẫn vượt qua theo kiểu ngẫu nhiên; thứ chặn được nó là một điều kiện `if` bằng Python
(best match < 0,5 → buộc từ chối), kiểm được, không phụ thuộc tâm trạng của model. Hai: **test
với hệ AI phải chạy lại nhiều lần, kể cả khi không đổi code** — vì thứ thay đổi không phải code
của mình mà là hành vi của model. "Đã pass" chỉ có nghĩa là "đã pass ở lần chạy đó".

## 4. Nếu làm lại từ đầu, tôi đổi gì

- **Viết golden set trước khi viết rule, không phải sau.** Vụ GS15 (regex meta quá hẹp) lẽ ra
  không tồn tại nếu tôi nhặt 20 câu hỏi thật từ chatlog ra làm case chuẩn TRƯỚC rồi mới viết
  regex khớp chúng. Thứ tự đúng là "nhìn data → chốt case → viết rule", tôi đã làm ngược ở tầng
  tín hiệu và trả giá bằng một lượt fail.
- **Chạy case AI live nhiều lượt liên tiếp ngay từ đầu** (3–5 lần cùng một case) thay vì mỗi
  lượt một lần — độ flaky của model là thứ phải đo, không phải thứ phát hiện tình cờ như vụ GS11.
- **Đo chi phí quota sớm hơn.** Giữa chừng chúng tôi cạn 100K token/ngày của Groq ngay trước
  giờ chạy thử — sau đó mới thêm cache kết quả và fallback model. Nếu tính trước "một lượt eval
  full tốn bao nhiêu token × chạy mấy lượt/ngày" thì đã không có 1 giờ 40 phút ngồi chờ quota reset.

## 5. Kỹ năng AI product tôi mang về sau sự kiện

- **Biến "chất lượng" thành thứ đo được**: tách chiều (đúng-có-căn-cứ / đúng nguyên nhân gốc /
  trung thực khi không biết), mỗi chiều một định nghĩa pass/fail mà người ngoài nhóm chấm ra
  cùng kết quả — thay vì "thấy trả lời ổn".
- **Quality bar chốt trước, giữ nguyên, ghi cả lượt fail**: bảng kết quả của tôi có lượt 94%
  và lượt 95% CHƯA ĐẠT nằm cạnh lượt 100% — và chính hai lượt fail đó là hai phát hiện giá trị
  nhất của cả phần kiểm thử.
- **Thiết kế hệ AI theo nguyên tắc "AI làm việc ngôn ngữ, số liệu và an toàn là của code"**:
  mọi con số do Python đếm, AI chỉ đặt tên; và tầng an toàn cuối (grounding guard) cũng là code.
  Sai ở tầng AI thì khó chịu, sai ở tầng số liệu thì mất niềm tin — kiến trúc phải bảo vệ tầng sau.
- **Test hệ non-deterministic khác test phần mềm thường**: pass một lần không có nghĩa là an
  toàn; cần chạy lặp, cần guard bằng code, và cần golden set sống cùng sản phẩm (mỗi lần sửa
  rule/prompt là chạy lại trọn bộ, không chạy lẻ case vừa sửa).
