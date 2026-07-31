# Reflection —  Phạm Mai Anh · 2A202601681 · phần phụ trách: Xử lý dữ liệu + Phân tích chatlog

## 1. Tôi đã làm gì (cụ thể, trỏ về file/commit)

Tôi phụ trách hai module nền tảng mà toàn bộ pipeline phụ thuộc vào:

**`data_prep.py` — đọc, chuẩn hoá và nhóm chatlog:**
- `SELECTION_RE`: regex tách 3 thành phần từ content thô của học viên — trang, đoạn bôi đen, câu hỏi gõ tay. Format gốc của VLearn trộn cả ba vào một trường `content` duy nhất, cần tách ra mới phân tích được ngữ cảnh câu hỏi.
- `build_turns()`: ghép cặp `student` và `tutor` theo `turn_id`, lọc bỏ turn lẻ, chuẩn hoá sang dict phẳng để `signals.py` và dashboard dùng trực tiếp.
- `to_vn_datetime()`: chuyển timestamp UTC sang giờ Việt Nam (+7) — dữ liệu gốc lưu UTC, nếu không chuyển thì nhóm ngày bị sai (tin nhắn 23:30 UTC thành ngày hôm sau theo VN).
- `group_by_day()`: trả về `dict` thường thay vì `defaultdict` — lý do ghi rõ trong docstring.
- `list_available_days()`: cung cấp danh sách ngày có data để dashboard render dropdown chọn ngày.

**`llm_client.py` — client dùng chung cho toàn bộ lời gọi AI:**
- Thiết kế `get_client()` đọc `GROQ_API_KEY` qua `python-dotenv` từ file `.env` cùng thư mục — không hardcode, không lộ key khi demo.
- Viết `create_with_retry()`: wrapper retry tối đa 3 lần khi Groq trả về lỗi `tool_use_failed` — lỗi này quan sát được là flaky (cùng prompt lúc pass lúc không), retry lại thường qua ngay mà không cần đổi prompt.
- Viết `to_function_tool()`: helper chuẩn hoá schema sang format `{"type": "function", ...}` mà Groq/OpenAI yêu cầu — giúp `classify_friction.py` và `agent_tutor.py` khai báo tool gọn hơn.

---

## 2. Quyết định khó nhất tôi tham gia + vì sao chọn phương án đó

**Quyết định: `group_by_day()` dùng `dict` thường + `.setdefault()` thay vì `defaultdict(lambda: defaultdict(list))`.**

Ban đầu tôi viết tự nhiên bằng `defaultdict` lồng nhau — gọn hơn, trực quan hơn. Nhưng khi Hoa Mai tích hợp vào dashboard và bật `@st.cache_data`, hàm bị lỗi `pickle` vì `lambda` lồng trong hàm không serialize được.

Có hai hướng xử lý: (A) bỏ cache Streamlit, (B) viết lại không dùng `lambda`. Tôi chọn (B) vì cache là tính năng quan trọng — data pack đầy đủ ~1.261 turns, mỗi lần chọn ngày mà parse lại từ đầu sẽ chậm thấy rõ khi demo. Viết lại bằng `.setdefault()` mất thêm vài phút nhưng giữ được cả hai: cache hoạt động và code vẫn đọc được.

Bài học từ quyết định này: **module không tồn tại độc lập** — `data_prep.py` trông như code thuần Python nhưng cách nó trả dữ liệu ảnh hưởng trực tiếp đến constraint của tầng trên (Streamlit caching). Phải biết downstream dùng mình như thế nào mới thiết kế đúng.

---

## 3. Một thứ đã sai / suýt sai và tôi học được gì

**Sai: quên chuyển timezone, nhóm ngày bị lệch.**

Lúc đầu `build_turns()` dùng thẳng `message_created_at` gốc để nhóm ngày mà không qua `to_vn_datetime()`. Khi chạy thử, một số tin nhắn tối ngày 27/07 giờ VN lại rơi vào ngày 28/07 trong dashboard — vì timestamp lưu UTC, 23:30 UTC = 06:30 sáng hôm sau giờ VN.

Lỗi này không gây crash — số liệu vẫn ra, nhìn bề ngoài dashboard vẫn chạy — nên dễ bỏ sót nếu không có người đối chiếu thực tế. Phát hiện được nhờ Phượng khi chạy golden set thấy số lượt ngày 27/07 thấp bất thường so với kỳ vọng từ mining ban đầu.

Sau khi sửa, tôi thêm `to_vn_datetime()` thành bước bắt buộc trong `build_turns()` và ghi chú rõ trong `group_by_day()` — ai đọc code cũng thấy ngay giờ đã được chuẩn hoá trước khi đến hàm này.

**Học được:** dữ liệu sai im lặng nguy hiểm hơn crash. Crash thì biết ngay để sửa; số liệu lệch nhẹ mà "trông ổn" có thể đi đến demo mà không ai phát hiện. Cần có số baseline để đối chiếu, không chỉ chạy xem có ra output không.

---

## 4. Nếu làm lại từ đầu, tôi đổi gì

**Viết test kiểm tra `build_turns()` sớm hơn — trước khi tích hợp vào pipeline.**

Tôi build `data_prep.py` theo kiểu "chạy được rồi xem kết quả" — in ra số turns, nhìn vài dòng đầu, thấy hợp lý thì chuyển sang bước tiếp. Lỗi timezone phát hiện muộn vì không có assertion nào kiểm tra "số turns ngày X phải nằm trong khoảng Y–Z".

Nếu làm lại, tôi sẽ viết thêm vài assert đơn giản ngay trong `__main__` block: tổng turns, phân bố theo ngày, số turns lẻ bị bỏ qua — để bất kỳ ai chạy `python data_prep.py` cũng thấy ngay nếu parse bị hỏng do thay đổi format CSV.

**Thứ hai: thống nhất interface sớm hơn với Phương trước khi viết.**

`build_turns()` trả về list of dict với các key cụ thể. Một lần Phương gọi `turn['day']` thay vì `turn['day_code']` — không crash vì dict chỉ trả `None` khi key không tồn tại, bug chạy thầm lặng đến khi debug. Nếu dùng `dataclass` hoặc `TypedDict` từ đầu, IDE/Python sẽ bắt lỗi này ngay.

---

## 5. Kỹ năng AI product tôi mang về sau sự kiện

**Kiến trúc "AI không đổi số liệu":** phần quan trọng nhất tôi học được không phải từ code mà từ quyết định thiết kế của nhóm — Python đếm và gom cụm, AI chỉ đặt tên. Lúc đầu tôi nghĩ đây là giải pháp vì giới hạn token của Groq free tier. Nhưng làm xong mới thấy đây là nguyên tắc: **kết quả AI phải kiểm lại được bằng tay**. Nếu AI tự tính cả số liệu lẫn đặt tên, giảng viên không có cách nào biết số 55,4% đến từ đâu. Tách ra thì quote nguyên văn + số đếm của Python làm căn cứ độc lập — AI sai tên cụm cũng không kéo sai số.

**Đọc lỗi thật trước khi thiết kế retry:** `create_with_retry()` trong `llm_client.py` chỉ retry `tool_use_failed`, không retry tất cả lỗi. Quyết định đó đến từ quan sát thực tế — lỗi này flaky, lần sau thường qua; còn lỗi khác (auth, rate limit) retry ngay không giải quyết được gì. Thiết kế retry tốt cần biết *loại lỗi nào* có thể tự hồi phục, không phải retry mọi thứ cho chắc.

**Data module là cam kết:** sau sự kiện này tôi hiểu rõ hơn rằng khi viết hàm trả dữ liệu cho module khác, mình đang ký một hợp đồng ngầm về schema và behavior. Đổi key tên hay đổi kiểu trả về là phá hợp đồng đó — và trong team 5 người build song song, phá hợp đồng im lặng còn nguy hiểm hơn bug bình thường.
