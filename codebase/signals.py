"""KHỐI 1 — Rule-based friction signal detection. KHÔNG gọi AI.

Phân loại theo đúng 3 nhóm friction trong canvas "AI Learning Analytics Copilot" (CP1):
  1. TUTOR LIMITATION   — AI Tutor chưa hỗ trợ được (không tìm thấy tài liệu / thiếu context /
                           trả lời chưa đúng câu hỏi)
  2. LEARNING DIFFICULTY — học viên có dấu hiệu chưa hiểu (hỏi lại cùng khái niệm / cần giải
                           thích nhiều lần / có hiểu nhầm kiến thức)
  3. LEARNING INTENT DRIFT — không tập trung vào mục tiêu học (câu hỏi ngoài phạm vi / chào hỏi,
                           hỏi vui / tương tác không liên quan)

Không dùng từ khoá cảm xúc ("không hiểu"...) làm tín hiệu chính — quá hiếm (~1% mẫu khi mining),
dùng tổ hợp hành vi đếm được thay thế (xem spec.md §1).
"""
import re
import collections
from transcript_index import keywords  # noqa: F401 (dùng ở classify_friction.py qua import chung)

GREETING_RE = re.compile(r'^(hello+|hi+|hey+|chào|xin chào|alo+|test|hê lô|helo|yo)\b.{0,10}$', re.I)
FAIL_RE = re.compile(
    r'(không tìm thấy|rất tiếc|không thể truy cập|chưa tìm thấy|'
    r'hệ thống tìm kiếm không|không có thông tin|không tìm được)', re.I
)
# Câu hỏi về chính con AI / meta, ngoài phạm vi bài giảng — ví dụ canvas: "Bạn là model nào?"
META_RE = re.compile(r'(bạn là (model|ai) nào|bạn tên là gì|bạn là ai|thời tiết)', re.I)

# Học viên tự nói ra mình đang bối rối — tín hiệu BỔ SUNG cho learning_difficulty, không phải
# tín hiệu chính (spec.md §1: từ khoá cảm xúc quá hiếm ~1% mẫu, nhưng khi CÓ thì rất chắc chắn).
CONFUSION_RE = re.compile(
    r'(không hiểu|chưa hiểu|khó hiểu|hiểu nhầm|hiểu sai|vẫn (chưa|không) (hiểu|rõ)|'
    r'rối quá|confused|mình bị rối|giải thích lại|nói lại)', re.I
)

REPEAT_PAGE_THRESHOLD = 3  # ngưỡng đã chốt trong spec.md §1 (dòng "Số liệu chính" #5)

CATEGORIES = ('tutor_limitation', 'learning_difficulty', 'intent_drift')


def classify_input_type(question):
    """Phân loại thô 1 câu hỏi học viên — dùng để suy ra 'intent_drift'."""
    q = question.lower().strip().strip('?.!')
    if len(q) == 0:
        return 'rỗng'
    if GREETING_RE.match(q):
        return 'chào hỏi/test'
    if META_RE.search(q):
        return 'meta/ngoài phạm vi'
    if len(q) <= 3:
        return 'cụt'
    if len(q) <= 15:
        return 'rất ngắn'
    return 'câu hỏi tự gõ'


def _is_rephrase_pair(q_a, q_b, min_shared=3):
    """Tín hiệu 'đổi diễn đạt hỏi lại cùng khái niệm' — heuristic đã dùng lúc mining."""
    a, b = q_a.lower().strip(), q_b.lower().strip()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) >= min_shared and len(wb) >= min_shared


def classify_turn_categories(turn):
    """1 turn (1 câu hỏi + 1 câu trả lời) -> set các nhóm áp dụng.

    tutor_limitation và intent_drift là tín hiệu MỨC TURN (áp dụng ngay ở 1 lượt);
    learning_difficulty cần nhìn nhiều turn trong 1 hội thoại, tính riêng ở
    compute_conversation_signals().
    """
    cats = set()
    if FAIL_RE.search(turn['tutor_content']):
        cats.add('tutor_limitation')
    input_type = classify_input_type(turn['question'])
    if input_type in ('chào hỏi/test', 'cụt', 'rỗng', 'meta/ngoài phạm vi'):
        cats.add('intent_drift')
    return cats


def compute_conversation_signals(conv_turns):
    """conv_turns: list turn dict (đã sort theo thời gian) của CÙNG 1 conversation_id."""
    pages = [t['page'] for t in conv_turns if t['page']]
    page_counts = collections.Counter(pages)
    repeated_page_max = max(page_counts.values()) if page_counts else 0
    repeated_page_flag = repeated_page_max >= REPEAT_PAGE_THRESHOLD

    rephrase_flag = False
    for i in range(1, len(conv_turns)):
        if _is_rephrase_pair(conv_turns[i - 1]['question'], conv_turns[i]['question']):
            rephrase_flag = True
            break

    direct_answer_count = sum(1 for t in conv_turns if t['move_used'] == 'give_direct_answer')

    confusion_count = sum(1 for t in conv_turns if CONFUSION_RE.search(t['question']))

    rating_down_quit = bool(conv_turns) and conv_turns[-1]['rating'] == 'down'

    per_turn_cats = [classify_turn_categories(t) for t in conv_turns]
    tutor_limitation_count = sum(1 for c in per_turn_cats if 'tutor_limitation' in c)
    intent_drift_count = sum(1 for c in per_turn_cats if 'intent_drift' in c)

    # NHÓM 2 — Learning Difficulty: cần góc nhìn nhiều turn (lặp/đổi diễn đạt/ép đáp án/bỏ cuộc/
    # tự nói "không hiểu")
    learning_difficulty_flag = (
        repeated_page_flag or rephrase_flag or direct_answer_count >= 1 or rating_down_quit
        or confusion_count >= 1
    )

    categories_present = set()
    if tutor_limitation_count > 0:
        categories_present.add('tutor_limitation')
    if learning_difficulty_flag:
        categories_present.add('learning_difficulty')
    if intent_drift_count > 0:
        categories_present.add('intent_drift')

    # Độ ưu tiên hiển thị khi 1 hội thoại rơi vào nhiều nhóm cùng lúc: tutor_limitation
    # (hệ thống lỗi, cần sửa ngay) > learning_difficulty (cần TA can thiệp) > intent_drift (thấp nhất)
    primary_category = next((c for c in CATEGORIES if c in categories_present), None)

    return {
        'repeated_page_max': repeated_page_max,
        'repeated_page_flag': repeated_page_flag,
        'rephrase_flag': rephrase_flag,
        'direct_answer_count': direct_answer_count,
        'confusion_count': confusion_count,
        'rating_down_quit': rating_down_quit,
        'tutor_limitation_count': tutor_limitation_count,
        'intent_drift_count': intent_drift_count,
        'learning_difficulty_flag': learning_difficulty_flag,
        'categories': sorted(categories_present),
        'primary_category': primary_category,
        'friction_flag': bool(categories_present),
        'distinct_pages': sorted(page_counts.keys()),
        'n_turns': len(conv_turns),
    }


def build_day_cases(day_conversations):
    """day_conversations: dict conversation_id -> [turn, ...] (output của data_prep.group_by_day[date]).

    Trả về input chuẩn hoá cho Khối 2: danh sách case có friction_flag=True + tổng số hội thoại
    trong ngày (mẫu số để Khối 2 tính %), cùng breakdown rule-based theo 3 nhóm (đã đếm được,
    không cần AI mới có con số này — Khối 2 chỉ cần đặt TÊN khái niệm + tinh chỉnh nguyên nhân).
    """
    cases = []
    category_counts = {c: 0 for c in CATEGORIES}
    for conv_id, turns in day_conversations.items():
        sig = compute_conversation_signals(turns)
        if not sig['friction_flag']:
            continue
        for c in sig['categories']:
            category_counts[c] += 1
        cases.append({
            'conversation_id': conv_id,
            'signals': sig,
            'turns': [
                {
                    'turn_id': t['turn_id'],
                    'page': t['page'],
                    'question': t['question'],
                    'tutor_snippet': t['tutor_content'][:180],
                    'tutor_fail': bool(FAIL_RE.search(t['tutor_content'])),
                }
                for t in turns
            ],
        })
    total = len(day_conversations)
    return {
        'total_conversations': total,
        'friction_cases': cases,
        'n_friction_cases': len(cases),
        'category_breakdown': {
            c: {'count': category_counts[c], 'percent': round(category_counts[c] / max(total, 1) * 100, 1)}
            for c in CATEGORIES
        },
    }


if __name__ == '__main__':
    from data_prep import load_chatlog, build_turns, group_by_day

    rows = load_chatlog('../data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv')
    turns = build_turns(rows)
    by_day = group_by_day(turns)

    for date in sorted(by_day):
        report = build_day_cases(by_day[date])
        b = report['category_breakdown']
        print(f"{date}: {report['n_friction_cases']}/{report['total_conversations']} hội thoại có friction "
              f"| tutor_limitation={b['tutor_limitation']['percent']}% "
              f"learning_difficulty={b['learning_difficulty']['percent']}% "
              f"intent_drift={b['intent_drift']['percent']}%")
