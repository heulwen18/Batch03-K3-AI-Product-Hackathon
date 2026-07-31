"""KHỐI 2 — Lời gọi AI THẬT: đặt tên khái niệm + viết gợi ý hành động cho các cụm friction.

Đây là "quyết định AI trung tâm" của lát cắt (spec.md §4).

KIẾN TRÚC (đã đổi sau khi phát hiện Groq free tier giới hạn 12.000 token/phút — payload
gửi toàn bộ case thô của ngày đông (71 case) cần ~37.000 token, vượt giới hạn):
  1. Python (rule-based, KHÔNG AI) gom case theo (category, từ khoá đại diện) thành CỤM,
     tính SẴN case_count/percent_of_day/root_cause chính xác — số liệu không bao giờ do AI đoán.
  2. AI (Groq) CHỈ nhận danh sách cụm đã tóm tắt (nhỏ, không phụ thuộc số case trong ngày) và
     làm việc nó giỏi nhất: đặt tên khái niệm dễ hiểu + viết cause_rationale/suggested_action.
  3. Python merge lại thành kết quả cuối — giữ đúng hình dạng cũ nên dashboard.py/agent_demo_ui.py
     không cần đổi gì.

Mỗi case đã được Khối 1 gắn sẵn category cố định (tutor_limitation / learning_difficulty /
intent_drift) ở case['signals']['primary_category'] — Khối 2 không được tự đổi category.
"""
import collections
import json

from transcript_index import search as transcript_search, keywords as extract_keywords
from llm_client import get_client, to_function_tool, create_with_retry, DEFAULT_MODEL

MODEL = DEFAULT_MODEL
MAX_CLUSTERS_TO_LLM = 25  # giữ payload nhỏ, không phụ thuộc số case trong ngày (log rõ nếu cắt bớt)
RETRIEVAL_BUG_THRESHOLD = 0.5  # match_ratio >= ngưỡng này mà tutor vẫn fail -> lỗi tìm kiếm, không phải thiếu nội dung

CATEGORY_LABELS = {
    "tutor_limitation": "AI Tutor chưa hỗ trợ được (không tìm thấy tài liệu / thiếu context / trả lời chưa đúng câu hỏi)",
    "learning_difficulty": "học viên có dấu hiệu chưa hiểu (hỏi lại cùng khái niệm / cần giải thích nhiều lần / hiểu nhầm kiến thức)",
    "intent_drift": "không tập trung vào mục tiêu học (câu hỏi ngoài phạm vi / chào hỏi, hỏi vui / tương tác không liên quan)",
}

NAMING_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "named_clusters": {
            "type": "array",
            "description": "Mỗi phần tử ứng với ĐÚNG 1 cụm đã cho trong input, theo cluster_id — không tự bịa cụm mới, không bỏ sót cụm nào.",
            "items": {
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "string", "description": "PHẢI khớp đúng cluster_id đã cho trong input."},
                    "concept": {"type": "string", "description": "Tên ngắn gọn, cụ thể, dễ hiểu cho giảng viên (vd 'ReAct agent pattern', không phải 'AI nói chung'). Với category='intent_drift' có thể đặt tên chung 'Chào hỏi / câu hỏi ngoài phạm vi'."},
                    "cause_rationale": {"type": "string", "description": "1 câu giải thích, PHẢI dựa vào category/root_cause/transcript_match_ratio đã cho trong cụm — không suy diễn thêm ngoài dữ liệu được cấp."},
                    "suggested_action": {
                        "type": "string",
                        "description": (
                            "Gợi ý hành động 1 câu, PHÙ HỢP root_cause đã cho: content_gap -> TA giảng lại/gửi tài liệu bổ sung; "
                            "retrieval_bug -> báo đội kỹ thuật sửa tìm kiếm (không cần giảng lại); "
                            "learning_difficulty -> TA giảng lại hoặc trả lời trực tiếp khái niệm này; "
                            "intent_drift -> không cần can thiệp giảng dạy, chỉ ghi nhận."
                        ),
                    },
                },
                "required": ["cluster_id", "concept", "cause_rationale", "suggested_action"],
            },
        },
        "low_confidence_note": {
            "type": "string",
            "description": "Ghi chú nếu nhiều cụm có case_count quá ít (<3) nên độ tin cậy thấp — để trống nếu không có.",
        },
    },
    "required": ["named_clusters"],
}

NAMING_TOOL = to_function_tool(
    "submit_cluster_names",
    "Đặt tên khái niệm + viết gợi ý hành động cho từng cụm friction đã được tính số sẵn.",
    NAMING_TOOL_SCHEMA,
)

SYSTEM_PROMPT = """Bạn là trợ lý phân tích cho giảng viên khoá học AI ("AI Learning Analytics \
Copilot"). Bạn nhận một danh sách CỤM (cluster) — mỗi cụm đã được tính SẴN bằng rule-based \
Python: category (tutor_limitation / learning_difficulty / intent_drift), case_count, \
percent_of_day, root_cause (content_gap / retrieval_bug / khong_ap_dung), transcript_match_ratio, \
và vài ví dụ câu hỏi nguyên văn.

Việc DUY NHẤT của bạn: với MỖI cụm, (1) đặt 1 tên khái niệm ngắn gọn dễ hiểu dựa trên các ví dụ \
câu hỏi, (2) viết 1 câu cause_rationale giải thích dựa ĐÚNG vào root_cause/match_ratio đã cho, \
(3) viết 1 câu suggested_action phù hợp root_cause.

Quy tắc bắt buộc:
- KHÔNG tự tính lại case_count/percent_of_day/root_cause — những số đó đã đúng, chỉ dùng để viết rationale.
- KHÔNG bỏ sót cụm nào, KHÔNG tự thêm cụm mới ngoài danh sách được cho.
- Với root_cause='content_gap': rationale phải nói "transcript_matches yếu/rỗng trong 6 buổi được cấp, \
  có thể giảng viên đã dạy ở buổi khác ngoài data này" — KHÔNG khẳng định tuyệt đối "chưa từng dạy".
- Gọi tool submit_cluster_names để trả kết quả, không trả lời bằng văn xuôi tự do."""


def _cluster_key_for_case(case):
    """(category, từ khoá đại diện) — dùng làm khoá gom cụm. Từ khoá đại diện = từ dài nhất
    (proxy đơn giản cho độ đặc trưng) trong câu hỏi đã gộp của case, rule-based, kiểm lại được.
    """
    combined = ' '.join(t['question'] for t in case['turns'])
    kws = extract_keywords(combined)
    rep_keyword = max(kws, key=len) if kws else '(không rõ)'
    return case['signals']['primary_category'], rep_keyword


def build_clusters(cases, index, total_conversations):
    """Gom case thành cụm — 100% rule-based. Trả về list cụm đã có đủ số liệu chính xác,
    sắp xếp theo case_count giảm dần.
    """
    groups = collections.defaultdict(list)
    for case in cases:
        groups[_cluster_key_for_case(case)].append(case)

    clusters = []
    for (category, rep_keyword), group_cases in groups.items():
        combined_query = ' '.join(t['question'] for c in group_cases for t in c['turns'])
        matches = transcript_search(combined_query, index, k=1)
        best_match_ratio = round(matches[0]['match_ratio'], 2) if matches else 0.0

        root_cause = 'khong_ap_dung'
        if category == 'tutor_limitation':
            root_cause = 'retrieval_bug' if best_match_ratio >= RETRIEVAL_BUG_THRESHOLD else 'content_gap'

        example_turns = [c['turns'][0] for c in group_cases[:3]]
        clusters.append({
            'cluster_id': f"{category}::{rep_keyword}",
            'category': category,
            'case_count': len(group_cases),
            'percent_of_day': round(len(group_cases) / max(total_conversations, 1) * 100, 1),
            'root_cause': root_cause,
            'transcript_match_ratio': best_match_ratio,
            'transcript_excerpt': matches[0]['excerpt'][:150] if matches else '',
            'example_turn_ids': [t['turn_id'] for t in example_turns],
            'example_quotes': [t['question'][:120] for t in example_turns],
        })
    clusters.sort(key=lambda c: c['case_count'], reverse=True)
    return clusters


def build_user_payload(date, day_report, clusters):
    kept = clusters[:MAX_CLUSTERS_TO_LLM]
    dropped = len(clusters) - len(kept)
    payload = {
        "ngay": date,
        "tong_so_hoi_thoai_trong_ngay": day_report['total_conversations'],
        "so_hoi_thoai_co_tin_hieu_friction": day_report['n_friction_cases'],
        "category_labels": CATEGORY_LABELS,
        "clusters": kept,
    }
    if dropped > 0:
        payload["ghi_chu_cat_bot"] = (
            f"Đã cắt bớt {dropped} cụm case_count thấp nhất để giữ payload gọn "
            f"(giữ lại {len(kept)}/{len(clusters)} cụm, ưu tiên case_count cao)."
        )
    return payload


def classify_day(date, day_report, index, api_key=None, model=MODEL, dry_run=True):
    """Trả về (prompt_payload, result). result có field 'concepts' cùng hình dạng như trước
    (concept/category/case_count/percent_of_day/root_cause/cause_rationale/example_turn_ids/
    example_quote/suggested_action) để dashboard.py/agent_demo_ui.py không cần đổi gì.
    """
    clusters = build_clusters(day_report['friction_cases'], index, day_report['total_conversations'])
    payload = build_user_payload(date, day_report, clusters)

    if dry_run:
        return payload, None

    client = get_client(api_key)
    resp = create_with_retry(
        client,
        model=model,
        max_tokens=4000,
        tools=[NAMING_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_cluster_names"}},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    msg = resp.choices[0].message
    if not msg.tool_calls:
        raise RuntimeError(f"Model không gọi tool submit_cluster_names — finish_reason={resp.choices[0].finish_reason}, content={msg.content!r}")

    named = None
    for tc in msg.tool_calls:
        if tc.function.name == "submit_cluster_names":
            named = json.loads(tc.function.arguments)
            break
    if named is None:
        raise RuntimeError("Không tìm thấy tool_call submit_cluster_names hợp lệ.")

    name_by_id = {n['cluster_id']: n for n in named.get('named_clusters', [])}
    concepts = []
    for c in payload['clusters']:
        n = name_by_id.get(c['cluster_id'])
        concepts.append({
            'concept': n['concept'] if n else c['cluster_id'],
            'category': c['category'],
            'case_count': c['case_count'],
            'percent_of_day': c['percent_of_day'],
            'root_cause': c['root_cause'],
            'cause_rationale': n['cause_rationale'] if n else '[AI không trả về tên cho cụm này — dùng dữ liệu thô]',
            'example_turn_ids': c['example_turn_ids'],
            'example_quotes': c['example_quotes'],  # list, cùng thứ tự với example_turn_ids
            'example_quote': c['example_quotes'][0] if c['example_quotes'] else '',
            'suggested_action': n['suggested_action'] if n else '',
        })
    result = {'concepts': concepts, 'low_confidence_note': named.get('low_confidence_note', '')}
    return payload, result


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

    print(f"=== Ngày {date} — {day_report['n_friction_cases']}/{day_report['total_conversations']} hội thoại friction "
          f"-> {len(payload['clusters'])} cụm ===")
    if dry:
        print("(dry-run — chưa gọi AI thật, cần GROQ_API_KEY trong codebase/.env + chạy lại với --live)")
        print(f"Payload sẽ gửi cho model: {len(json.dumps(payload, ensure_ascii=False))} ký tự.")
        print("\nMẫu 3 cụm đầu tiên (để kiểm tra thủ công trước khi tốn quota):")
        print(json.dumps(payload['clusters'][:3], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
