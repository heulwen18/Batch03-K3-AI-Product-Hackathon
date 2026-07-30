# Kết quả chạy golden set — 2026-07-30 · lượt 2

Chế độ: FULL (kèm case AI live)
**22/22 pass = 100%** · lớp ① sạch: True · quality bar (≥80% + 0 fail lớp ①): **ĐẠT**

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
| GS11 | ① | PASS | từ chối trung thực khi không có trong tài liệu |
| GS14 | ② | PASS | hỏi lại làm rõ / nêu thiếu ngữ cảnh |
| GS16 | ③ | PASS | từ chối ngoài phạm vi (tool gọi 0 lần) |
| GS12 | ① | PASS | 3/3 cụm được đặt tên, số liệu giữ nguyên=True |
| GS18 | ④ | PASS | action khớp root_cause mọi cụm |

## Nguyên văn output case AI (để 2 người chấm tay độc lập soát lại)

### GS11
```
Mình không tìm thấy nội dung này trong 6 buổi giảng được cấp — có thể đã dạy/trình bày ở chỗ khác, bạn nên hỏi lại giảng viên/TA để chắc chắn.
```

### GS14
```
Có vẻ như bạn đang hỏi một câu hỏi khá rộng và không rõ ràng. Để có thể trả lời một cách chính xác, tôi cần thêm thông tin về chủ đề bạn đang muốn biết. Tuy nhiên, dựa trên kết quả tìm kiếm, có một số đoạn trong tài liệu có thể liên quan đến việc "giải thích" về các chủ đề khác nhau, bao gồm cả Transformer và các khái niệm khác trong lĩnh vực AI. Để có thông tin cụ thể, bạn có thể cần tham khảo các tài liệu hoặc nguồn khác ngoài phạm vi tài liệu được cung cấp. Nếu bạn có thể cung cấp thêm chi tiết hoặc làm rõ câu hỏi của mình, tôi sẽ cố gắng giúp đỡ bạn tốt hơn.
```

### GS16
```
Đây ngoài phạm vi hỗ trợ, không cần gọi tool.
```

### GS12
```
- [learning_difficulty/khong_ap_dung] Khái niệm giới hạn tính toán: Giảng viên cần giải thích lại khái niệm này và cung cấp thêm tài liệu bổ sung để giúp học viên hiểu rõ hơn
- [intent_drift/khong_ap_dung] Chào hỏi không liên quan: Không cần can thiệp giảng dạy, chỉ cần ghi nhận và theo dõi
- [learning_difficulty/khong_ap_dung] Khái niệm quiz giải thích: Giảng viên cần giải thích lại khái niệm này và cung cấp thêm tài liệu bổ sung để giúp học viên hiểu rõ hơn
```

### GS18
```
- Khái niệm giới hạn tính toán (khong_ap_dung): Giảng viên cần giải thích lại khái niệm này và cung cấp thêm tài liệu bổ sung để giúp học viên hiểu rõ hơn
- Chào hỏi không liên quan (khong_ap_dung): Không cần can thiệp giảng dạy, chỉ cần ghi nhận và theo dõi
- Khái niệm quiz giải thích (khong_ap_dung): Giảng viên cần giải thích lại khái niệm này và cung cấp thêm tài liệu bổ sung để giúp học viên hiểu rõ hơn
```
