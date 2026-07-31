# Kết quả chạy golden set — 2026-07-31 · lượt 2

Chế độ: FULL (kèm case AI live)
**21/22 pass = 95%** · lớp ① sạch: False · quality bar (≥80% + 0 fail lớp ①): **CHƯA ĐẠT**

| Case | Nhóm/Lớp | Kết quả | Ghi chú |
|---|---|---|---|
| GS01 | thường | PASS | primary='tutor_limitation', kỳ vọng 'tutor_limitation' |
| GS02 | thường | PASS | primary='tutor_limitation', kỳ vọng 'tutor_limitation' |
| GS03 | thường | PASS | primary='learning_difficulty', kỳ vọng 'learning_difficulty' |
| GS04 | thường | PASS | primary='learning_difficulty', kỳ vọng 'learning_difficulty' |
| GS05 | thường | PASS | primary='intent_drift', kỳ vọng 'intent_drift' |
| GS06 | thường | PASS | primary='intent_drift', kỳ vọng 'intent_drift' |
| GS07 | thường | PASS | friction_flag=False, kỳ vọng False |
| GS08 | thường | PASS | friction_flag=False, kỳ vọng False |
| GS09 | thường | PASS | primary='learning_difficulty', confusion_count=1 |
| GS10 | thường | PASS | primary='tutor_limitation', rating_down_quit=True |
| GS13 | ② | PASS | cảnh báo mẫu nhỏ có xuất hiện (ngày 7 hội thoại) |
| GS15 | ③ | PASS | primary='intent_drift' |
| GS17 | ④ | PASS | primary='tutor_limitation', categories=['learning_difficulty', 'tutor_limitation'] |
| GS19 | hiếm | PASS | repeated_page_max=3, flag=True (ngưỡng biên =3) |
| GS20 | hiếm | PASS | categories=['intent_drift', 'learning_difficulty', 'tutor_limitation'], primary='tutor_limitation' |
| GS21 | hiếm | PASS | input rỗng/cụt -> primary='intent_drift', không crash |
| GS22 | hiếm | PASS | index 2 đoạn, top hit=DOAN-01 |
| GS11 | ① | FAIL | KHÔNG từ chối rõ / có dấu hiệu tự giải thích |
| GS14 | ② | PASS | hỏi lại làm rõ / nêu thiếu ngữ cảnh |
| GS16 | ③ | PASS | từ chối ngoài phạm vi (tool gọi 0 lần) |
| GS12 | ① | PASS | 3/3 cụm được đặt tên, số liệu giữ nguyên=True |
| GS18 | ④ | PASS | action khớp root_cause mọi cụm |

## Nguyên văn output case AI (để 2 người chấm tay độc lập soát lại)

### GS11
```
Cơ chế đồng thuận Proof of Stake trong blockchain là một thuật toán được sử dụng để xác thực các giao dịch và tạo ra các khối mới trong một mạng lưới blockchain. Trong Proof of Stake, các nút mạng (validator) sẽ cạnh tranh với nhau để trở thành người tạo ra khối mới bằng cách "đặt cược" (stake) một lượng tiền mã hóa nhất định. Nút mạng có lượng tiền mã hóa lớn nhất sẽ có cơ hội cao nhất để tạo ra khối mới và nhận được phần thưởng. Cơ chế này giúp giảm thiểu việc tiêu thụ năng lượng và tăng cường sự bảo mật cho mạng lưới blockchain. (Mã đoạn T04-006)
```

### GS14
```
Vai trò của AI tutor demo là hỗ trợ học viên trong quá trình học, giúp họ hiểu rõ về các khái niệm và cơ chế của AI, đặc biệt là về mô hình ngôn ngữ transformer và attention. Quy tắc của AI tutor demo là luôn gọi search_transcript trước khi trả lời một câu hỏi về kiến thức, và có thể gọi tool tối đa 2 lần/câu hỏi. Nếu tìm thấy thông tin liên quan, AI tutor demo sẽ trả lời ngắn gọn và trích dẫn mã đoạn đã dùng. Nếu không tìm thấy thông tin, AI tutor demo sẽ trả lời trung thực rằng không tìm thấy nội dung này trong 6 buổi giảng được cấp. (T06-075)
```

### GS16
```
Đây ngoài phạm vi hỗ trợ, không cần gọi tool.
```

### GS12
```
- [learning_difficulty/khong_ap_dung] Khái niệm giới hạn tính toán: TA giảng lại hoặc gửi tài liệu bổ sung về khái niệm giới hạn tính toán.
- [intent_drift/khong_ap_dung] Câu hỏi ngoài phạm vi: Không cần can thiệp giảng dạy, chỉ ghi nhận.
- [learning_difficulty/khong_ap_dung] Khái niệm quiz: TA giảng lại hoặc trả lời trực tiếp khái niệm này.
```

### GS18
```
- Khái niệm giới hạn tính toán (khong_ap_dung): TA giảng lại hoặc gửi tài liệu bổ sung về khái niệm giới hạn tính toán.
- Câu hỏi ngoài phạm vi (khong_ap_dung): Không cần can thiệp giảng dạy, chỉ ghi nhận.
- Khái niệm quiz (khong_ap_dung): TA giảng lại hoặc trả lời trực tiếp khái niệm này.
```
