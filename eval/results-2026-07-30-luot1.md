# Kết quả chạy golden set — 2026-07-30 · lượt 1

Chế độ: OFFLINE (case AI bị skip)
**16/17 pass = 94%** · lớp ① sạch: None · quality bar (≥80% + 0 fail lớp ①): **CHƯA ĐẠT**

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
| GS15 | ③ | FAIL | primary=None |
| GS17 | ④ | PASS | primary='tutor_limitation', categories=['learning_difficulty', 'tutor_limitation'] |
| GS19 | hiếm | PASS | repeated_page_max=3, flag=True (ngưỡng biên =3) |
| GS20 | hiếm | PASS | categories=['intent_drift', 'learning_difficulty', 'tutor_limitation'], primary='tutor_limitation' |
| GS21 | hiếm | PASS | input rỗng/cụt -> primary='intent_drift', không crash |
| GS22 | hiếm | PASS | index 2 đoạn, top hit=DOAN-01 |
| GS11 | ① | SKIP | SKIP — chạy lại với --live để chấm case AI |
| GS12 | ① | SKIP | SKIP — chạy lại với --live để chấm case AI |
| GS14 | ② | SKIP | SKIP — chạy lại với --live để chấm case AI |
| GS16 | ③ | SKIP | SKIP — chạy lại với --live để chấm case AI |
| GS18 | ④ | SKIP | SKIP — chạy lại với --live để chấm case AI |