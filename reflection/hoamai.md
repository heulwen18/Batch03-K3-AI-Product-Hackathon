```markdown
# Reflection — [Họ và tên] · [Mã học viên]

**Phần phụ trách:** Frontend và tích hợp hệ thống (50%), Slide và demo (50%)

## 1. Tôi đã làm gì

- Xây dựng frontend Streamlit gồm ba màn hình chính: **Live Dashboard, Conversation và Report**.
- Tích hợp dữ liệu chatlog thật vào giao diện, xử lý bộ lọc thời gian và cập nhật số liệu theo khoảng ngày được chọn.
- Hiển thị kết quả phân loại hội thoại, bằng chứng liên quan, số liệu tổng hợp và gợi ý hành động cho giảng viên/TA.
- Tham gia xây dựng khoảng 50% nội dung, bố cục và storyline cho `demo-slides.pdf`, tập trung vào luồng: vấn đề → giải pháp → kiểm thử → validation.

## 2. Quyết định khó nhất

Quyết định khó nhất là thiết kế giao diện sao cho giảng viên không chỉ nhìn thấy số liệu tổng quan mà còn có thể truy ngược về hội thoại gốc để kiểm chứng.

Nhóm chọn luồng:

> Dashboard → hội thoại gốc → phân tích AI → hành động đề xuất.

Cách này giúp người dùng hiểu insight đến từ đâu và không phải tin kết quả AI một cách mù quáng. Nhóm cũng tách rõ phần rule-based dùng để tính số liệu và phần AI dùng để phân loại, giải thích và đề xuất hành động.

## 3. Điều đã sai và bài học

Khi tích hợp dữ liệu thật, tôi gặp lỗi timezone và kiểu dữ liệu khiến bộ lọc thời gian không hoạt động đúng. Tôi phải chuẩn hóa dữ liệu thời gian và kiểm tra lại điều kiện lọc để không mất dữ liệu ở ngày cuối.

Tôi cũng nhận ra rằng giao diện đẹp chưa đủ nếu số liệu không chính xác hoặc người dùng không tìm được bằng chứng. Từ case GS15, tôi học được rằng một rule tưởng đúng vẫn có thể bỏ sót những cách diễn đạt khác nhau, vì vậy golden set rất cần thiết để phát hiện lỗi và kiểm tra lại toàn bộ hệ thống.

## 4. Nếu làm lại

- Test wireframe với người dùng trước khi code giao diện chi tiết.
- Chốt sớm schema giữa backend và frontend.
- Thiết kế rõ các trạng thái loading, lỗi API, low-confidence và correction.
- Quản lý `session_state` và cache ngay từ đầu để tránh mất dữ liệu hoặc gọi lại API không cần thiết.
- Xây dựng slide sớm theo đúng chuỗi: pain → AI decision → prototype → evaluation → validation.

## 5. Bài học mang về

Tôi học được cách phân chia hợp lý giữa rule-based và AI, cách tích hợp dữ liệu thật vào frontend và cách xây dựng giao diện có evidence, confidence và khả năng kiểm chứng.

Bài học quan trọng nhất là một sản phẩm AI tốt không chỉ tạo ra kết quả, mà còn phải giúp người dùng hiểu kết quả đến từ đâu, biết khi nào nên tin và có thể đưa ra hành động tiếp theo.
```
