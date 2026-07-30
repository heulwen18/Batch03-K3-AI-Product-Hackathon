# AI SPEC — Bản đồ Vướng Mắc Lớp (Class Friction Map) · Nhóm [CẦN ĐIỀN] · Zone [CẦN ĐIỀN]
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

## §1. User & Job

- **Job executor:** Giảng viên/TA đang dạy khoá AI Thực Chiến — cụ thể là người chuẩn bị nội dung ôn tập / office-hours sau mỗi buổi hoặc mỗi ngày học.
- **Core JTBD** (không tên sản phẩm/AI): *"Xác định khái niệm nào lớp đang vướng nhiều nhất sau mỗi buổi học, để ưu tiên đúng chỗ khi ôn tập hoặc trả lời trên lớp."*
  - Tự kiểm: bỏ AI đi, việc này còn tồn tại không? → Còn — giảng viên vẫn cần biết lớp vướng gì dù có AI hay không, chỉ là hiện tại chỉ có thể đọc tay từng đoạn chat hoặc chờ học viên tự hỏi trên lớp.
- **Problem statement** (KHÔNG chữ AI): Giảng viên dạy lớp ~1.000 học viên qua nhiều buổi, không có cách nào nhanh để biết học viên đang vướng cụ thể khái niệm nào trong lúc tự học ngoài giờ lên lớp. Cách duy nhất hiện tại là đọc thủ công từng tin nhắn (hàng nghìn dòng) hoặc chờ học viên hỏi trực tiếp trên lớp — nên các khoảng trống kiến thức thường chỉ lộ ra muộn, khi học viên đã làm bài/dự án sai.
- **Evidence (chuẩn A và/hoặc B — log đầy đủ trong repo):**

  ### Đường B — Mining (đã xong, dùng data pack có sẵn)

  - Nguồn: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` (1.261 turn ghép cặp học viên–tutor, 585 hội thoại, 369 học viên, 8 ngày 22/07–29/07) + 6 transcript bài giảng (~700 đoạn có mã `[Txx-NNN]`).
  - Phương pháp đếm: parse field `content` học viên tách phần "đoạn được chọn" khỏi câu hỏi gõ tay; phân loại theo regex/từ khoá theo từng nhóm bên dưới; so khớp từ khoá (đã chuẩn hoá bỏ dấu) giữa câu hỏi và 700 đoạn transcript để xác định khái niệm có được dạy tường minh hay không. Toàn bộ script mining kiểm lại được (không cần chạy lại LLM).
  - Số liệu chính:
    | # | Phát hiện | Số đếm | Nguồn |
    |---|---|---|---|
    | 1 | Câu hỏi dạng "X là gì?" nhắm vào khái niệm **không xuất hiện** trong 6 transcript được cấp | 43/61 (70%) | vd. [T0990] `"Context" là gì`, [T0338] `agent la gi` |
    | 2 | Cụm "agent/ReAct" bị hỏi nhiều nhất, riêng từ "ReAct" xuất hiện 0/6 transcript | 144 lượt / 84 học viên riêng biệt | topic-match trên `content` |
    | 3 | Tutor trả lời "không tìm thấy tài liệu" | 258/1.261 lượt (20.5%) | regex trên `tutor.content` |
    | 4 | Trong số (3), nội dung **thực ra có** trong transcript (khớp ≥50% từ khoá) — tức là lỗi retrieval, không phải thiếu nội dung | 118/258 (46%) | vd. [T0905] hỏi tóm tắt Day 04 → giảng viên đang giảng đúng phần đó ở [T06-075] |
    | 5 | Hội thoại có hỏi lặp lại cùng 1 trang ≥3 lần | 47/585 (8%) | vd. hội thoại C0050 hỏi lại trang 11 × 4 lần |
    | 6 | Hội thoại có đổi cách diễn đạt để hỏi lại cùng khái niệm | 112/585 (19.1%) | vd. C0011: [T1091]→[T0780] cùng chủ đề "sinh văn bản" |
    | 7 | Tutor buộc phải dùng nước đi `give_direct_answer` (bỏ Socratic, đưa thẳng đáp án) | 146/1.261 (11.6%) | field `move_used` |
    | 8 | Rating "down" rồi học viên im lặng bỏ cuộc ngay | 23/33 hội thoại có rating down (70%) | field `rating` |
    | 9 | Tín hiệu "chào hỏi/test/cụt/rỗng" — có thể lẫn vào nhóm friction nếu không tách riêng | 65/1.261 (5.1%) | vd. [T0986] `hi bro`, [T0025] `t đẹp trai mà` |
  - ≥5 quote/ví dụ nguyên văn (ngắn, đúng luật bảo mật data — không dán nguyên văn dài):
    - [T0905] *"tóm gọn những nội dung quan trọng nhất trong day 04 này"* → tutor: "không tìm thấy tài liệu tổng hợp..." (dù giảng viên đã giảng đúng phần này ở [T06-075])
    - [T1220] *"không hiểu gì"*
    - [T0638] *"chào bạn, mình chưa hiểu về RAG"*
    - [T0338] *"agent la gi"*
    - [T0397] *"Giải thích đoạn bôi đen ở Trang 3: 'Tool'"* — tutor trả lời không trích dẫn, rating down

  ### Đường A — Khảo sát (nhóm tự làm, cung cấp sau)

  - Số liệu mining / kết quả khảo sát (n = ?, % xác nhận):
  - Log câu hỏi + từng câu trả lời nguyên văn:

## §2. Impact & quyết định chọn

- **Bảng impact ≥3 ứng viên** (nhóm đã thảo luận qua 3 ứng viên trước khi chốt):

  | Ứng viên | Bao nhiêu người gặp | Tần suất | Mỗi lần tốn gì | Build nổi trong sự kiện? |
  |---|---|---|---|---|
  | (1) Cảnh báo real-time học viên bị kẹt cho TA | ≥112/585 hội thoại có tín hiệu lặp/đổi diễn đạt (19.1%) | Liên tục mỗi buổi học | Học viên bỏ cuộc (70% sau rating down); nhưng **0/1.261 lượt tutor từng escalate cho TA**, 100% hội thoại là 1-1 học viên–tutor → vai trò "TA giám sát VLearn" chưa xác nhận tồn tại | Khó — cần hạ tầng real-time + xác nhận job executor có thật |
  | (2) Two-tier grounding cho khái niệm ngoài giáo trình | 84 học viên hỏi cụm agent/ReAct; 70% câu "X là gì" không có trong transcript | Liên tục, khái niệm bị hỏi nhiều nhất khoá | Rủi ro học sai kiến thức (bịa) hoặc bị chặn giữa buổi (từ chối cứng) | Trung bình — cần crawl/biên tập nguồn ngoài trước, tốn thời gian chuẩn bị nội dung, rủi ro lớp ④ nếu nội dung ngoài lệch cách khoá dạy |
  | **(3) [CHỌN] Bản đồ vướng mắc lớp cho giảng viên** | Giảng viên/TA — ít người trực tiếp dùng nhưng ảnh hưởng gián tiếp toàn bộ ~1.000 học viên | Cần mỗi buổi/mỗi ngày (8 ngày dữ liệu = tối thiểu 8 lần cần biết) | Không biết nên ôn ở đâu → ôn sai chỗ hoặc bỏ sót lỗ hổng thật (46% case "không tìm thấy" là lỗi tool chứ không phải thiếu nội dung — hai nguyên nhân cần phân biệt) → lỗ hổng tích luỹ đến khi thi mới lộ | **Dễ nhất — 100% dùng data tĩnh đã có sẵn (CSV), không cần hạ tầng real-time hay nguồn ngoài** |

- **Ứng viên ĐÃ LOẠI + vì sao:**
  - (1) loại vì job executor "TA theo dõi VLearn real-time" chưa có bằng chứng tồn tại (0/1.261 lượt escalate) — rủi ro xây tính năng cho vai trò có thể không có thật; muốn giữ lại phải khảo sát xác nhận trước.
  - (2) loại vì cần thời gian biên tập/crawl nguồn ngoài trước sự kiện, không kịp trong khung 1,5 ngày; đồng thời rủi ro lớp ④ (nội dung ngoài không khớp cách khoá dạy) cao hơn.
- **Ứng viên CHỌN + vì sao (bằng số):** Chọn (3) vì (a) tận dụng toàn bộ evidence mining đã có sẵn (9 số liệu ở §1, không cần thu thêm data mới), (b) job executor có thật và rõ ràng hơn — giảng viên chắc chắn đang đứng lớp và cần chuẩn bị nội dung ôn tập, (c) build được trọn vẹn trong thời gian sự kiện vì không phụ thuộc hạ tầng real-time hay nguồn dữ liệu ngoài.

## §3. Giải pháp tương tự đã nghiên cứu

*[CẦN NHÓM LÀM — guide §2.2: mỗi thành viên tự dùng thử 1 sản phẩm gần giống (ChatGPT study mode / Khanmigo / NotebookLM / Duolingo / Quizlet AI...), trả lời đúng 4 câu (flow / điều đáng học / điều đáng né / mình khác gì) rồi điền vào đây. Tôi không có quyền tự bịa phần "quan sát cụ thể" vì nó đòi hỏi dùng thử thật.]*

- [Sản phẩm 1]: flow / đáng học / đáng né / mình khác gì
- [Sản phẩm 2]: ...

## §4. Thiết kế

- **Lát cắt MỘT CÂU:** Giảng viên chuẩn bị ôn tập/office-hours cuối ngày · muốn biết lớp đang vướng khái niệm nào và vì sao · AI phân loại friction hành vi từ chatlog trong ngày rồi đối chiếu khái niệm đó có được dạy rõ trong transcript hay không · kết quả là bảng top 3-5 khái niệm vướng nhất kèm nguyên nhân (dạy chưa rõ / tutor tìm sai) và ví dụ nguyên văn.
- **Non-goals (≥3 thứ KHÔNG build):**
  1. Không cảnh báo real-time trong lúc học viên đang chat (đó là ứng viên (1) đã loại).
  2. Không tự động sinh nội dung/slide dạy lại — chỉ chỉ ra vướng ở đâu và vì sao, giảng viên tự quyết định cách dạy lại.
  3. Không định danh học viên cụ thể trong báo cáo — chỉ tổng hợp cấp lớp, tránh rủi ro riêng tư.
  4. Không dùng nhãn "mất tập trung" làm kết luận chính thức — vì tín hiệu quá yếu (~5%, dễ lẫn với học viên chỉ test tool), chỉ hiển thị như ghi chú phụ có gắn "độ tin cậy thấp".
- **Mức prototype nhắm tới:** [ ] Sketch [x] Mock [ ] Working *(đề xuất — nhóm xác nhận lại)* — phần AI thật: bước phân loại friction + đối chiếu transcript (LLM call thật trên dữ liệu mẫu từ chatlog); phần mock: giao diện dashboard giảng viên (dữ liệu tĩnh, không cần real-time).
- **Automation:** [ ] augment [x] conditional [ ] automate — *(đề xuất augment thuần, xem cân nhắc dưới)*. Lý do theo cost-of-error: output chỉ là gợi ý tổng hợp cấp lớp, giảng viên luôn là người quyết định có dạy lại hay không; nếu AI phân loại sai vài case thì cái giá là giảng viên nhìn nhầm hướng một buổi (rẻ, tự phát hiện được khi đối chiếu ví dụ nguyên văn kèm theo), không ảnh hưởng trực tiếp đến học viên.
- **§4b. Nguyên tắc đã áp dụng** *(≥4 — dự kiến, cần xác nhận lại vị trí cụ thể khi có prototype thật — [CẦN NHÓM XÁC NHẬN]):*

  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---|
  | G2 — làm rõ AI tốt đến đâu | Dòng chú thích đầu dashboard: "phân loại dựa trên tín hiệu hành vi (lặp trang, đổi diễn đạt...), không đọc được cảm xúc thật, có thể sai với case cá biệt" |
  | G10 — thu hẹp phạm vi khi nghi ngờ | Hội thoại chỉ có 1-2 tín hiệu yếu (dưới ngưỡng) → xếp "chưa đủ chắc để kết luận", không ép vào 1 nhãn friction |
  | G11 — giải thích vì sao | Mỗi dòng trong bảng kết quả kèm ví dụ nguyên văn + mã turn/đoạn transcript để giảng viên tự kiểm tra lại |
  | G9 — sửa dễ dàng | Giảng viên đánh dấu "phân loại sai" ngay trên dòng kết quả, không cần sửa ở nơi khác |
  | PAIR — Explainability & Trust | Hiển thị % kèm cỡ mẫu (n=?) thay vì chỉ số tổng quát, để giảng viên tự đánh giá độ tin |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

| # | Tình huống cụ thể | Lớp | Hành vi mong muốn | Nguyên tắc áp |
|---|---|---|---|---|
| 1 | Học viên hỏi "ReAct là gì" nhiều lần nhưng 6 transcript được cấp chưa từng nhắc từ "ReAct" | ① Nguồn sự thật | Báo "khái niệm không xuất hiện trong 6 buổi được cấp — có thể đã dạy ở buổi khác ngoài data này, cần giảng viên xác nhận", không khẳng định chắc "chưa từng dạy" | G10, G11 |
| 2 | Khái niệm "agent" bị hỏi nhiều (144 lượt) nhưng tutor fail thấp (7.6%) — hỏi nhiều có thể chỉ vì khái niệm khó/hay, không phải vì thiếu nội dung | ① Nguồn sự thật | Không tự động gắn "vướng mắc" chỉ vì volume cao — phải kết hợp với tỷ lệ fail/tín hiệu friction hành vi thật, không suy diễn nhân-quả sai | G2 |
| 3 | 1 hội thoại chỉ lặp trang 2 lần (dưới ngưỡng 3 đã định nghĩa ở §1) | ② Mơ hồ/thiếu thông tin | Xếp vào "tín hiệu yếu", không đưa vào top friction chính thức | G10 |
| 4 | Một ngày dữ liệu quá ít hội thoại (vd ngày nghỉ, <20 lượt) | ② Mơ hồ/thiếu thông tin | Báo "mẫu quá nhỏ, độ tin cậy thấp" thay vì đưa % gây hiểu lầm | G10, G11 |
| 5 | Field `rating` chỉ có ở 2.8% tin nhắn — phần lớn hội thoại không có | ② Mơ hồ/thiếu thông tin | Không dùng rating làm tín hiệu bắt buộc, chỉ làm tín hiệu bổ sung khi có sẵn | G2 |
| 6 | Giảng viên yêu cầu "cho tôi biết chính xác học viên nào đang yếu nhất" | ③ Ngoài phạm vi/thẩm quyền | Từ chối nêu danh tính cá nhân, chỉ trả lời tổng hợp cấp lớp; gợi ý cách khác nếu giảng viên cần hỗ trợ 1-1 (vd tự hỏi thăm trên lớp) | Non-goal, G17 |
| 7 | Giảng viên muốn AI tự sinh luôn slide/nội dung dạy lại | ③ Ngoài phạm vi/thẩm quyền | Từ chối — chỉ ra vướng ở đâu và vì sao, không tự soạn nội dung giảng dạy thay giảng viên | Non-goal |
| 8 | Nhóm tín hiệu "mất tập trung" (~5%: chào hỏi/cụt/rỗng) bị lẫn với "không hiểu bài" | ④ Đặc thù domain | Tách riêng nhãn phụ "độ tin cậy thấp / có thể chỉ đang test tool", không gộp chung vào báo cáo friction chính — nếu gộp nhầm, giảng viên dạy lại sai chỗ, tốn thời gian buổi học thật | G2, G10 |
| 9 | 46% case tutor báo "không tìm thấy" thực ra transcript có nội dung khớp — nếu báo cáo không phân biệt, giảng viên tưởng nhầm là lỗi giảng dạy | ④ Đặc thù domain | Luôn tách 2 nguyên nhân trong output: "nội dung chưa dạy rõ" (cần dạy lại) vs "hệ thống tìm sai" (không cần dạy lại, chỉ cần báo team kỹ thuật) | G11 |
| 10 | Học viên gõ sai chính tả/không dấu khiến so khớp từ khoá bỏ sót case thật | ① Nguồn sự thật | Chuẩn hoá (bỏ dấu, lowercase) trước khi so khớp; nếu vẫn không chắc, xếp "chưa đủ chắc" thay vì bỏ qua im lặng | G10 |

## §6. Bốn đường đi của trải nghiệm

- **Happy path:** Đủ tín hiệu rõ ràng (≥3 lần lặp trang hoặc rephrase rõ ràng + khái niệm cụ thể xác định được) → xếp đúng nhóm friction, đối chiếu transcript, xuất dòng báo cáo kèm ví dụ nguyên văn + nguyên nhân.
- **Low-confidence (②):** Tín hiệu yếu hoặc mẫu nhỏ (dưới ngưỡng đã định nghĩa, hoặc ngày có <20 hội thoại) → gắn nhãn "độ tin cậy thấp", không đưa vào top ưu tiên chính.
- **Failure/không căn cứ (①):** Khái niệm không tìm thấy trong 6 transcript được cấp → nói rõ giới hạn ("chỉ dựa trên 6 buổi được cấp"), không khẳng định "chưa từng dạy".
- **Correction:** Giảng viên đánh dấu 1 dòng phân loại sai ngay trên báo cáo → ghi nhận lại (dùng để cải thiện ngưỡng, không tự động sửa ngầm).
- **Khi bị đòi ngoài phạm vi (③):** Giảng viên đòi danh tính học viên cụ thể hoặc đòi AI soạn sẵn nội dung dạy lại → từ chối, giải thích lý do (riêng tư / ngoài phạm vi thiết kế), gợi ý việc thay thế (xem log ẩn danh, tự soạn dựa trên gợi ý).
- **Case đặc thù domain (④):** Tín hiệu "mất tập trung" (chào hỏi/cụt/rỗng, ~5%) → luôn tách riêng khỏi nhóm "không hiểu bài", không gộp chung để tránh giảng viên dạy lại sai chỗ.

## §7. Kiểm thử

- **Chiều chất lượng + định nghĩa kiểm chứng được:**
  1. *Đúng phân loại friction* — pass/fail: 2 thành viên chấm tay độc lập cùng 10-15 case, kết quả phải trùng nhau ≥ ngưỡng nhóm tự chốt (guide §2.6 bước 4).
  2. *Đúng nguyên nhân (dạy chưa rõ vs tutor tìm sai)* — pass/fail: mọi kết luận phải trace được về turn_id/message_id cụ thể + đoạn transcript khớp (hoặc không khớp) tương ứng.
  3. *An toàn phạm vi* — pass/fail cứng: output cấp-lớp không bao giờ nêu danh tính/user_id học viên cụ thể.
- **Golden set (≥20 case, file trong `eval/`):** cấu trúc theo guide §2.6 — ≥2 case/lớp (4 lớp × 2 = 8) + 8-10 case thường + 2-4 case hiếm; ≥10 case lấy trực tiếp từ chatlog thật. Có thể lấy ngay từ các turn_id đã liệt kê ở §1 và §5 làm điểm khởi đầu (vd [T0905], [T1220], [T0638], [T0397], C0050, C0011...), bổ sung thêm cho đủ 20+.
- **Quality bar** (chốt từ 23:59, giữ nguyên sau đó): "Đạt khi ≥ ___% qua bộ, và ___" — **[CẦN NHÓM CHỐT SỐ %]**, không thể tôi tự quyết định thay nhóm.
- **Kết quả các lượt chạy** (bảng % — cập nhật đến trước CP6): *[CẦN ĐIỀN sau khi build và chạy golden set]*

## §8. Phân công & kế hoạch

- **Phân công có tên:** spec / evidence / prompt / code / demo — *[CẦN ĐIỀN TÊN từng phần]*
- **Canvas CP1:** đang được 1 thành viên khác trong nhóm phụ trách.
- **Willing users (≥3 tên) + kế hoạch vòng validation CP5:** *[CẦN ĐIỀN — ưu tiên mời chính giảng viên/TA thật của khoá, vì họ là job executor trực tiếp]*. 3 câu hỏi dùng đúng theo guide §4.2: "Điều gì khó hiểu/khó chịu nhất?" · "Kết quả này bạn có tin không — vì sao?" · "Bạn có dùng thật không — vì sao/vì sao chưa?"
- **Multi-prototype (nếu làm):** *[CẦN ĐIỀN nếu nhóm dựng thêm phương án khác — ví dụ trục khác biệt: báo cáo dạng bảng vs dạng biểu đồ; ngưỡng friction cứng vs để giảng viên tự chỉnh ngưỡng]*

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| | | |
