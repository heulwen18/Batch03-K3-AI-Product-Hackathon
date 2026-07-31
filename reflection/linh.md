# Reflection — Lương Thị Linh · 2A202601015 · phần phụ trách: Thiết kế form khảo sát và frontend

## 1. Tôi đã làm gì (cụ thể, trỏ về file/commit)

- Tôi phụ trách thiết kế form khảo sát dành cho hai nhóm đối tượng là sinh viên và giảng viên. Form dành cho sinh viên tập trung vào trải nghiệm học tập, những khó khăn khi sử dụng AI Tutor và nhu cầu được hỗ trợ. Form dành cho giảng viên tập trung vào nhu cầu theo dõi tình hình học tập, nhận biết các vấn đề phổ biến và hỗ trợ sinh viên kịp thời.
- Khi thiết kế form, tôi tập trung vào cách sắp xếp câu hỏi, trường nhập liệu và các lựa chọn trả lời để nội dung rõ ràng, dễ hiểu và thuận tiện cho cả sinh viên lẫn giảng viên.
- Tôi tham gia xây dựng frontend Streamlit trong `codebase/app.py`, gồm ba khu vực chính: Chat với AI Tutor, Dashboard cho giảng viên/TA và Nhật ký hội thoại.
- Ở phần frontend, tôi tập trung vào bố cục giao diện, luồng chuyển giữa các tab, cách hiển thị số liệu, bộ lọc, bảng hội thoại và các trạng thái khi người dùng tương tác.
- Phạm vi công việc của tôi là thiết kế form khảo sát và hiện thực giao diện. Tôi không trực tiếp triển khai khảo sát, thu thập hoặc phân tích phản hồi, phỏng vấn người dùng hay thực hiện validation sản phẩm.

## 2. Quyết định khó nhất tôi tham gia + vì sao chọn phương án đó

- Quyết định khó nhất tôi tham gia là tổ chức frontend như thế nào để vừa thể hiện được trải nghiệm của học viên, vừa giúp giảng viên/TA theo dõi thông tin mà không làm giao diện quá phức tạp.
- Nhóm chọn xây dựng một ứng dụng Streamlit với ba tab thay vì tách thành nhiều sản phẩm độc lập. Ba tab tạo thành một luồng thống nhất: học viên hỏi AI Tutor → hội thoại được ghi nhận → giảng viên xem Dashboard và Nhật ký để theo dõi.
- Tôi chọn phương án này vì phù hợp với thời gian ngắn của hackathon, giảm công sức tích hợp và giúp người xem demo hiểu nhanh cách các phần của sản phẩm liên kết với nhau.
- Với form khảo sát sinh viên và giảng viên, tôi ưu tiên câu hỏi rõ ràng, số lượng trường vừa đủ và cách sắp xếp nội dung theo từng chủ đề. Trên giao diện sản phẩm, tôi cũng áp dụng cách tổ chức tương tự cho các form và bộ lọc để người dùng biết cần nhập gì và kết quả sẽ xuất hiện ở đâu.

## 3. Một thứ đã sai / suýt sai và tôi học được gì

- Ban đầu, tôi có xu hướng đưa quá nhiều thông tin và thành phần lên cùng một màn hình. Điều này khiến giao diện dễ bị rối, đặc biệt khi Dashboard có nhiều số liệu, bộ lọc và bảng hội thoại.
- Sau đó, tôi điều chỉnh lại bố cục, nhóm các thành phần có liên quan và ưu tiên những thông tin quan trọng xuất hiện trước. Các chi tiết bổ sung được đặt ở khu vực phù hợp để người dùng chỉ xem khi cần.
- Khi code frontend bằng Streamlit, tôi nhận ra ứng dụng sẽ rerun sau nhiều thao tác. Nếu không quản lý `session_state` và cache cẩn thận, lịch sử chat hoặc dữ liệu người dùng vừa nhập vào form có thể bị mất, đồng thời API có thể bị gọi lại không cần thiết.
- Tôi học được cách phân biệt dữ liệu của phiên hiện tại, dữ liệu cần giữ lại giữa các lần rerun và kết quả cần lưu bền vững. Đây là phần quan trọng để form và giao diện hoạt động ổn định.

## 4. Nếu làm lại từ đầu, tôi đổi gì

- Tôi sẽ phác thảo wireframe cho form và từng tab trước khi bắt đầu code để thống nhất sớm về bố cục, thứ tự thông tin và luồng thao tác.
- Tôi sẽ xây dựng các thành phần giao diện nhỏ, có thể tái sử dụng, thay vì viết toàn bộ giao diện trong một khối lớn. Cách này giúp việc chỉnh sửa và kiểm tra frontend nhanh hơn.
- Tôi sẽ xác định rõ trạng thái của từng form ngay từ đầu, bao gồm trạng thái chưa nhập, đang xử lý, thành công và có lỗi, để giao diện luôn phản hồi rõ ràng với người dùng.
- Tôi sẽ giảm lượng thông tin xuất hiện ở lần mở đầu tiên, đồng thời làm rõ hơn ý nghĩa của các tỷ lệ và điểm rủi ro trên Dashboard.
- Tôi cũng sẽ hoàn thiện luồng dữ liệu để hội thoại mới từ tab Chat được lưu bền vững và tự động cập nhật vào Dashboard. Hiện tại, hội thoại demo chỉ xuất hiện trong Nhật ký của phiên đang chạy.

## 5. Kỹ năng AI product tôi mang về sau sự kiện

- Tôi có thêm kinh nghiệm chuyển yêu cầu của một sản phẩm AI thành form khảo sát, bố cục và luồng tương tác cụ thể trên frontend.
- Tôi hiểu rõ hơn cách thiết kế câu hỏi phù hợp với từng nhóm đối tượng, tổ chức form khảo sát ngắn gọn, dùng nhãn dễ hiểu và sắp xếp các trường trả lời hợp lý.
- Tôi học được cách phân chia phần hiển thị giữa dữ liệu cố định và nội dung do AI tạo ra để người dùng có thể nhận biết rõ nguồn của thông tin.
- Tôi có thêm kinh nghiệm xây dựng frontend cho sản phẩm AI bằng Streamlit, đặc biệt là quản lý trạng thái hội thoại, hiển thị nguồn và bằng chứng, xử lý lỗi API, cache kết quả và duy trì dữ liệu qua các lần rerun.
- Điều quan trọng nhất tôi rút ra là giao diện của sản phẩm AI không chỉ cần đẹp mà còn phải giúp người dùng nhập thông tin thuận tiện, hiểu kết quả và biết bước tiếp theo cần thực hiện.
