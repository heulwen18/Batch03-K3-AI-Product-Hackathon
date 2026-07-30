"""KHỐI 2 — Lời gọi AI THẬT: phân loại friction theo khái niệm + nguyên nhân.

Đây là "quyết định AI trung tâm" của lát cắt (spec.md §4).
Input: output của Khối 1 (signals.build_day_cases) đã gắn thêm transcript match (Khối 1, rule-based).
Output: JSON có cấu trúc — ép bằng tool_use (forced tool call) để không phải tự parse text lỏng lẻo.
"""
import os
import json
from transcript_index import search as transcript_search

MODEL = "claude-sonnet-5"

REPORT_TOOL = {
    "name": "submit_friction_report",
    "description": "Nộp báo cáo vướng mắc lớp đã phân loại theo khái niệm cho 1 ngày học.",
    "input_schema": {
        "type": "object",
        "properties": {
            "concepts": {
                "type": "array",
                "description": "Danh sách cụm khái niệm/vấn đề, gom từ các case theo đúng category Khối 1 đã gắn sẵn ở mỗi case (signals.primary_category) — sắp xếp theo case_count giảm dần.",
                "items": {
                    "type": "object",
                    "properties": {
                        "concept": {"type": "string", "description": "Tên ngắn gọn, cụ thể (vd 'ReAct agent pattern', không phải 'AI nói chung'). Với nhóm intent_drift có thể để 1 cụm chung 'chào hỏi/câu hỏi ngoài phạm vi' thay vì tách theo khái niệm."},
                        "category": {
                            "type": "string",
                            "enum": ["tutor_limitation", "learning_difficulty", "intent_drift"],
                            "description": "PHẢI khớp với signals.primary_category của đa số case được gom vào cụm này — không tự suy diễn category khác.",
                        },
                        "case_count": {"type": "integer"},
                        "percent_of_day": {"type": "number", "description": "case_count / tong_so_hoi_thoai_trong_ngay * 100 — dùng đúng số đã cho, không tự bịa."},
                        "root_cause": {
                            "type": "string",
                            "enum": ["content_gap", "retrieval_bug", "khong_ap_dung"],
                            "description": (
                                "CHỈ áp dụng khi category='tutor_limitation': 'content_gap' nếu transcript_matches yếu/rỗng cho khái niệm này "
                                "(có thể giảng viên chưa dạy hoặc dạy ở buổi khác ngoài 6 buổi được cấp); 'retrieval_bug' nếu transcript_matches mạnh "
                                "(match_ratio>=0.5) NHƯNG tutor vẫn báo không tìm thấy — đây là lỗi hệ thống tìm kiếm, không phải lỗi giảng dạy. "
                                "Với category='learning_difficulty' hoặc 'intent_drift', luôn để 'khong_ap_dung'."
                            ),
                        },
                        "cause_rationale": {"type": "string", "description": "1 câu giải thích, trỏ vào bằng chứng cụ thể (match_ratio, số lần lặp/đổi diễn đạt...)."},
                        "example_turn_ids": {"type": "array", "items": {"type": "string"}},
                        "example_quote": {"type": "string", "description": "Trích ngắn 1 câu hỏi nguyên văn làm ví dụ."},
                        "suggested_action": {
                            "type": "string",
                            "description": (
                                "Gợi ý hành động 1 câu, PHÙ HỢP category: tutor_limitation+content_gap -> TA giảng lại/gửi tài liệu bổ sung; "
                                "tutor_limitation+retrieval_bug -> báo đội kỹ thuật sửa tìm kiếm (không cần giảng lại); "
                                "learning_difficulty -> TA giảng lại hoặc trả lời trực tiếp khái niệm này; "
                                "intent_drift -> không cần can thiệp giảng dạy, chỉ ghi nhận."
                            ),
                        },
                    },
                    "required": ["concept", "category", "case_count", "percent_of_day", "root_cause", "cause_rationale", "example_turn_ids", "suggested_action"],
                },
            },
            "low_confidence_note": {
                "type": "string",
                "description": "Ghi chú nếu mẫu ngày quá nhỏ hoặc có cụm case_count quá ít (<3) nên độ tin cậy thấp — để trống nếu không có.",
            },
        },
        "required": ["concepts"],
    },
}

SYSTEM_PROMPT = """Bạn là trợ lý phân tích cho giảng viên khoá học AI ("AI Learning Analytics \
Copilot"). Bạn nhận danh sách các hội thoại học viên–tutor trong 1 ngày học, MỖI CASE ĐÃ ĐƯỢC \
KHỐI 1 (rule-based) GẮN SẴN category ở field case['signals']['primary_category'] — một trong 3 \
nhóm cố định:
  - "tutor_limitation": AI Tutor chưa hỗ trợ được (không tìm thấy tài liệu / thiếu context / trả lời chưa đúng câu hỏi)
  - "learning_difficulty": học viên có dấu hiệu chưa hiểu (hỏi lại cùng khái niệm / cần giải thích nhiều lần / hiểu nhầm kiến thức)
  - "intent_drift": không tập trung vào mục tiêu học (câu hỏi ngoài phạm vi / chào hỏi, hỏi vui / tương tác không liên quan)

Việc của bạn KHÔNG phải tự nghĩ ra category mới — chỉ gom các case CÙNG category lại theo KHÁI NIỆM \
cụ thể (vd nhiều case tutor_limitation đều hỏi về "ReAct" thì gom chung 1 cụm "ReAct agent pattern"), \
đặt tên cụm, tính % , và (chỉ với tutor_limitation) tinh chỉnh thêm root_cause dựa vào transcript_matches \
đính kèm mỗi case.

Quy tắc bắt buộc:
- KHÔNG đổi category của case — chỉ dùng đúng category Khối 1 đã gắn.
- KHÔNG suy diễn "chưa được dạy" một cách tuyệt đối khi chọn root_cause=content_gap — chỉ nói \
  "transcript_matches yếu/rỗng trong 6 buổi được cấp", vì có thể giảng viên đã dạy ở buổi khác ngoài data này.
- Nếu 1 cụm chỉ có case_count < 3, vẫn báo cáo nhưng ghi rõ trong low_confidence_note.
- Không bịa case_count hay % — chỉ dùng đúng số case được cung cấp trong input.
- Gọi tool submit_friction_report để trả kết quả, không trả lời bằng văn xuôi tự do."""


def attach_transcript_matches(cases, index, k=2):
    """Với mỗi case, gộp câu hỏi các turn lại rồi tìm đoạn transcript khớp nhất (rule-based, không AI).
    Gộp ở mức case (không phải từng turn) để payload gọn — case-level match là đủ cho việc
    phân loại nguyên nhân "dạy chưa rõ" vs "tutor tìm sai".
    """
    for case in cases:
        combined_query = ' '.join(t['question'] for t in case['turns'])
        case['transcript_matches'] = [
            {'code': m['code'], 'match_ratio': round(m['match_ratio'], 2), 'excerpt': m['excerpt'][:150]}
            for m in transcript_search(combined_query, index, k=k)
        ]
        for turn in case['turns']:
            turn['tutor_snippet'] = turn['tutor_snippet'][:120]
    return cases


def build_user_payload(date, day_report):
    return {
        "ngay": date,
        "tong_so_hoi_thoai_trong_ngay": day_report['total_conversations'],
        "so_hoi_thoai_co_tin_hieu_friction": day_report['n_friction_cases'],
        # Số thật từ Khối 1 (rule-based) — model KHÔNG cần tự tính lại, chỉ tham chiếu để đối chiếu.
        "category_breakdown_tu_khoi_1": day_report['category_breakdown'],
        "cases": day_report['friction_cases'],
    }


def classify_day(date, day_report, index, api_key=None, model=MODEL, dry_run=True):
    """Trả về (prompt_payload, result). Nếu dry_run=True: không gọi API thật, result=None
    — dùng để kiểm tra prompt trước khi tốn quota, hoặc khi chưa có API key.
    """
    cases = attach_transcript_matches(day_report['friction_cases'], index)
    day_report = {**day_report, 'friction_cases': cases}
    payload = build_user_payload(date, day_report)

    if dry_run:
        return payload, None

    import anthropic  # import trễ — chỉ cần khi thực sự gọi API
    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        tools=[REPORT_TOOL],
        tool_choice={"type": "tool", "name": "submit_friction_report"},
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "submit_friction_report":
            return payload, block.input
    raise RuntimeError("Model không gọi tool submit_friction_report — kiểm tra lại prompt/model.")


if __name__ == '__main__':
    import sys
    from data_prep import load_chatlog, build_turns, group_by_day
    from signals import build_day_cases
    from transcript_index import load_transcript_paragraphs

    date = sys.argv[1] if len(sys.argv) > 1 else '2026-07-27'
    dry = '--live' not in sys.argv

    rows = load_chatlog('../data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv')
    turns = build_turns(rows)
    by_day = group_by_day(turns)
    index = load_transcript_paragraphs('../data/vlearn-pack/transcript')

    day_report = build_day_cases(by_day[date])
    payload, result = classify_day(date, day_report, index, dry_run=dry)

    print(f"=== Ngày {date} — {day_report['n_friction_cases']}/{day_report['total_conversations']} hội thoại friction ===")
    if dry:
        print("(dry-run — chưa gọi AI thật, cần ANTHROPIC_API_KEY + chạy lại với --live)")
        print(f"Payload sẽ gửi cho model: {len(json.dumps(payload, ensure_ascii=False))} ký tự, "
              f"{len(payload['cases'])} case, mỗi case có transcript_matches đính kèm.")
        print("\nMẫu 1 case đầu tiên (để kiểm tra thủ công trước khi tốn quota):")
        print(json.dumps(payload['cases'][0], ensure_ascii=False, indent=2)[:1500])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
