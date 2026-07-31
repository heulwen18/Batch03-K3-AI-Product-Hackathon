# Reflection — Cao Quế Phương · 2A202601111 · phần phụ trách: Build pipeline phân loại + tích hợp + train

## 1. Tôi đã làm gì 

- Tôi xây pipeline biến chatlog thành insight cho giảng viên. `codebase/data_prep.py` chuẩn hóa
  dữ liệu hỏi đáp; `codebase/signals.py` phát hiện ba nhóm tín hiệu gồm `tutor_limitation`,
  `learning_difficulty` và `intent_drift` ở cấp hội thoại. Tôi giữ lại nhiều nhãn tín hiệu nhưng
  dùng thứ tự ưu tiên cố định khi cần một nhãn chính, để các hội thoại vừa gặp lỗi tutor vừa thể
  hiện khó khăn học tập không bị mất thông tin.
- Trong `codebase/classify_friction.py`, tôi triển khai kiến trúc hai tầng: Python gom cụm và tính
  `case_count`, tỷ lệ, nguyên nhân gốc; AI chỉ đặt tên cụm, giải thích và gợi ý hành động. Tôi cũng
  tách lỗi tutor thành `retrieval_bug` và `content_gap` dựa trên mức khớp với transcript. Cách làm
  này giúp số liệu có thể kiểm lại và giảm payload ngày đông từ khoảng 37.000 token xuống danh
  sách tối đa 25 cụm, phù hợp giới hạn Groq free tier.

- Tôi tham gia tích hợp AI Tutor và cơ chế grounding trong `codebase/agent_tutor.py`. Khi kết quả
  retrieval dưới ngưỡng 0,5, hệ thống buộc tutor nói không đủ căn cứ thay vì trả lời bằng kiến
  thức nền. Đây là lớp bảo vệ rule-based bên ngoài prompt.
- Ở phần train, tôi fine-tune mô hình phân loại bốn lớp từ `vinai/phobert-base-v2`. Model card và
  checkpoint nằm ở `codebase/artifacts/model/`; kết quả từng thử nghiệm nằm trong
  `codebase/artifacts/*.json`. Tôi chia dữ liệu theo `conversation_id` với seed 42 để tránh một
  hội thoại xuất hiện ở cả train và test. Bản kết hợp 80 hội thoại gán nhãn tay với 30 hội thoại
  auto-label có trọng số 0,25 đạt accuracy 0,70 và macro-F1 0,6703 trên 20 hội thoại test.
## 2. Quyết định khó nhất tôi tham gia + vì sao chọn phương án đó

Quyết định khó nhất của tôi là chọn giữa một pipeline AI end-to-end và kiến trúc hybrid:
rule-based tính số liệu, AI chỉ xử lý phần ngôn ngữ. Ban đầu, việc gửi toàn bộ hội thoại cho LLM
có vẻ nhanh hơn vì model có thể vừa phân loại, vừa gom nhóm, vừa viết báo cáo. Tuy nhiên, payload
của ngày có 71 case lên tới khoảng 37.000 token, vượt giới hạn 12.000 token/phút. Quan trọng hơn,
nếu LLM tự tính số lượng hoặc phần trăm thì nhóm rất khó giải thích vì sao một chủ đề được xếp
hạng cao.

Tôi chọn kiến trúc hybrid vì cost-of-error của một con số sai lớn hơn chi phí của một tên cụm
chưa hay. Python giữ quyền quyết định đối với nhãn, số lượng và nguyên nhân gốc; LLM nhận tối đa
25 cụm đã tóm tắt và chỉ trả về `concept`, `cause_rationale`, `suggested_action`. Khi merge kết
quả, pipeline lấy lại toàn bộ con số từ dữ liệu gốc chứ không tin số do model sinh. Nhờ đó, app
vẫn hoạt động khi không gọi được AI và giảng viên luôn có thể truy ngược về hội thoại để kiểm tra.

Ở phần train, tôi cũng phải quyết định có nên dùng thêm nhãn tự động để bù cho lớp
`learning_difficulty` quá ít mẫu hay không. Tôi dùng 30 hội thoại auto-label nhưng giảm trọng số
loss xuống 0,25, đồng thời giữ tập test chỉ gồm nhãn tay và chia theo conversation. Đây là một
thử nghiệm có kiểm soát, không phải cách biến nhãn máy thành ground truth.

## 3. Một thứ đã sai / suýt sai và tôi học được gì

Điều suýt sai nhất là nhìn vào accuracy và kết luận mô hình train đã tốt. Bản chỉ train bằng nhãn
tay đạt accuracy 0,85, nghe cao hơn bản kết hợp dữ liệu đạt 0,70. Nhưng khi đọc theo từng lớp, mô
hình 0,85 dự đoán sai toàn bộ mẫu `learning_difficulty`: precision, recall và F1 đều bằng 0. Đây
lại chính là lớp quan trọng nhất đối với bài toán.

Thử nghiệm trên 17 hội thoại held-out độc lập còn cho kết quả thấp hơn nhiều: accuracy 0,2941,
macro-F1 0,2443; lớp `off_topic` và `normal` có F1 bằng 0. Điều này cho thấy split 20 hội thoại
quá nhỏ, phân bố nhãn mất cân bằng, và accuracy tổng có thể che giấu việc model bỏ sót lớp thiểu
số. Tôi học được rằng đánh giá mô hình phân loại không thể chỉ nhìn một metric đẹp. Tôi phải xem
macro-F1, recall theo lớp, confusion matrix, cách chia dữ liệu và đặc biệt là chất lượng trên dữ
liệu chưa từng tham gia quá trình phát triển.

## 4. Nếu làm lại từ đầu, tôi đổi gì

Nếu làm lại, tôi sẽ chốt taxonomy và hướng dẫn gán nhãn trước khi viết classifier. Tôi sẽ cho ít
nhất hai người gán nhãn độc lập, đo mức đồng thuận và giải quyết các case bất đồng. Với lớp
`learning_difficulty`, tôi sẽ chủ động lấy thêm hội thoại nhiều lượt thay vì dựa chủ yếu vào câu
đơn hoặc nhãn tự động.

Tôi cũng sẽ tạo ba tập tách biệt ngay từ đầu: train, validation và test khóa kín theo
`conversation_id`. Tập test chỉ được mở một lần sau khi đã chốt feature, threshold và trọng số.
Như vậy, metric cuối phản ánh khả năng tổng quát tốt hơn và tránh việc vô tình tối ưu theo test.

Về sản phẩm, tôi sẽ xây một baseline rule-based cùng bộ đo end-to-end trước khi fine-tune
PhoBERT. Sau đó mỗi thử nghiệm model phải chứng minh nó cải thiện recall của Learning Difficulty
mà không làm tăng quá nhiều false positive. Nếu chưa vượt baseline trên tập held-out đủ lớn, mô
hình chỉ nên chạy shadow mode để so sánh, chưa được thay pipeline chính.

## 5. Kỹ năng AI product tôi mang về sau sự kiện

Kỹ năng quan trọng nhất tôi mang về là thiết kế ranh giới trách nhiệm giữa code, model và con
người. Không phải phần nào có thể dùng AI cũng nên giao cho AI. Với dữ liệu cần đếm và kiểm lại,
rule-based phù hợp hơn; với việc đặt tên hoặc diễn đạt gợi ý, LLM tạo giá trị tốt hơn; còn quyết
định dạy lại nội dung nào vẫn thuộc về giảng viên.

Tôi cũng hiểu rõ hơn cách xây một vòng đời AI product hoàn chỉnh: bắt đầu từ pain có bằng chứng,
chuẩn hóa dữ liệu, định nghĩa nhãn, xây baseline, train theo split chống leakage, đánh giá bằng
metric theo lớp, phân tích failure, tích hợp vào UI và luôn cung cấp đường truy ngược về dữ liệu
gốc. Quan trọng nhất, một kết quả chưa tốt không phải thứ cần che đi. Nó là bằng chứng để xác định
model đang thiếu dữ liệu gì, sai ở đâu và có đủ an toàn để đưa vào sản phẩm hay chưa.

