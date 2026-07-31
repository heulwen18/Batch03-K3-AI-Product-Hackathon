# Reflection — Lương Thị Linh · 2A202601015 · phần phụ trách: Khảo sát người dùng, phỏng vấn validation và frontend

## 1. Tôi đã làm gì (cụ thể, trỏ về file/commit)

- Tôi tạo form khảo sát để thu thập thông tin về những khó khăn của học viên khi sử dụng AI Tutor, mức độ thường xuyên gặp vướng mắc và nhu cầu được giảng viên/TA hỗ trợ. Kết quả khảo sát được dùng để kiểm tra giả thuyết vấn đề trước khi nhóm chốt giải pháp.
- Tôi tham gia code frontend Streamlit trong `codebase/app.py`, gồm ba khu vực chính: Chat với AI Tutor, Dashboard cho giảng viên/TA và Nhật ký hội thoại. Các phần tôi tập trung gồm bố cục giao diện, luồng chuyển giữa ba tab, hiển thị số liệu, bộ lọc, bảng hội thoại và trạng thái khi người dùng tương tác.

## 2. Quyết định khó nhất tôi tham gia + vì sao chọn phương án đó

- Quyết định khó nhất tôi tham gia là tổ chức frontend như thế nào để giảng viên/TA cần nhìn được xu hướng của cả lớp và truy ngược về hội thoại gốc để kiểm chứng.
- Nhóm chọn xây dựng một ứng dụng Streamlit duy nhất với ba tab thay vì tách thành nhiều sản phẩm độc lập. Ba tab thể hiện một luồng thống nhất: học viên hỏi AI Tutor → hội thoại được ghi nhận → hệ thống phát hiện tín hiệu vướng mắc → giảng viên xem Dashboard và Nhật ký để quyết định hành động.
- Tôi chọn phương án này vì nó phù hợp với thời gian ngắn của hackathon, giảm công sức tích hợp và giúp người xem demo hiểu ngay mối liên hệ giữa trải nghiệm của học viên và insight dành cho giảng viên.
- Một quyết định quan trọng khác là để các số liệu rule-based hiển thị trước, còn AI chỉ đặt tên cụm, giải thích và đề xuất hành động sau khi người dùng chủ động bấm phân tích. Cách này giúp giao diện minh bạch hơn và người dùng phân biệt được đâu là số liệu có thể kiểm tra, đâu là nội dung do AI tạo ra.

## 3. Một thứ đã sai / suýt sai và tôi học được gì

- Ban đầu, tôi có xu hướng tập trung nhiều vào việc hoàn thiện giao diện và hỏi người dùng họ có “thích” sản phẩm hay không. Cách làm này suýt khiến validation chỉ thu được ý kiến chung, không chứng minh được sản phẩm có giải quyết một vấn đề thực tế hay không.
- Sau đó, tôi điều chỉnh kịch bản để người dùng thực hiện nhiệm vụ cụ thể trên prototype rồi mới trả lời ba câu hỏi cố định. Tôi cũng ghi lại nguyên văn lời nói và quan sát họ bấm vào đâu, mất bao lâu để tìm thông tin, thay vì chỉ ghi kết luận của bản thân.
- Vòng test cho thấy 4/5 người chủ động mở hội thoại gốc để kiểm chứng insight và 5/5 người quan tâm đến hành động tiếp theo hơn chi tiết kỹ thuật. Điều này giúp tôi nhận ra giao diện không chỉ cần trình bày biểu đồ đẹp mà phải hỗ trợ người dùng đi từ số liệu đến bằng chứng và quyết định.
- Khi code frontend bằng Streamlit, tôi cũng nhận ra ứng dụng sẽ rerun sau nhiều thao tác. Nếu không quản lý `session_state` và cache cẩn thận, lịch sử chat hoặc kết quả phân tích có thể bị mất và API có thể bị gọi lại. Tôi học được cách phân biệt dữ liệu lịch sử, dữ liệu của phiên hiện tại và kết quả cần lưu bền vững.

## 4. Nếu làm lại từ đầu, tôi đổi gì

- Tôi sẽ thực hiện khảo sát và các buổi phỏng vấn sớm hơn, trước khi chốt hoàn toàn cấu trúc frontend. Nhờ đó, nhóm có thể biết ngay thông tin nào giảng viên cần nhìn đầu tiên và tránh xây những thành phần ít được sử dụng.
- Tôi sẽ tạo wireframe đơn giản rồi test nhanh với một vài người trước khi code toàn bộ giao diện.
- Tôi sẽ xác định tiêu chí validation rõ ngay từ đầu, ví dụ: giảng viên có tìm được vấn đề cần ưu tiên trong vòng một phút không; họ có hiểu ý nghĩa tỷ lệ phần trăm không; và họ có truy được từ insight về hội thoại gốc không.
- Tôi sẽ giảm lượng thông tin xuất hiện ở lần mở đầu tiên, đồng thời làm rõ hơn ý nghĩa các tỷ lệ và điểm rủi ro. Đây là những vấn đề được nhiều người nhắc lại trong `validation/feedback-log.md`.
- Tôi cũng sẽ khép kín vòng lặp dữ liệu để hội thoại mới từ tab Chat được lưu bền vững và tự động cập nhật vào Dashboard. Hiện tại, hội thoại demo chỉ xuất hiện trong Nhật ký của phiên đang chạy.

## 5. Kỹ năng AI product tôi mang về sau sự kiện

- Tôi học được cách bắt đầu từ vấn đề và bằng chứng người dùng thay vì bắt đầu từ mô hình AI hoặc danh sách tính năng.
- Tôi hiểu rõ hơn cách thiết kế khảo sát và phỏng vấn: hỏi về hành vi thực tế, tránh câu hỏi dẫn dắt, ghi nhận nguyên văn và chuyển phản hồi thành thay đổi sản phẩm cụ thể.
- Tôi học được cách phân chia vai trò giữa logic cố định và AI: rule-based phù hợp với các con số, nhãn và tín hiệu cần kiểm tra; AI phù hợp với việc đặt tên vấn đề, giải thích và đề xuất hành động.
- Tôi có thêm kinh nghiệm xây dựng frontend cho sản phẩm AI, đặc biệt là quản lý trạng thái hội thoại, hiển thị nguồn và bằng chứng, xử lý lỗi API, cache kết quả và thiết kế luồng để người dùng không phải tin AI một cách mù quáng.
- Điều quan trọng nhất tôi mang về là một AI product tốt không chỉ cần tạo ra câu trả lời. Nó phải giúp người dùng hiểu bằng chứng, đánh giá mức độ tin cậy và đưa ra quyết định tiếp theo.
