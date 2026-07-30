"""Đọc chatlog CSV + transcript, chuẩn hoá thành cấu trúc dùng chung cho Khối 1/2.

Không gọi AI ở module này — chỉ parse/group dữ liệu thô.
"""
import csv
import re
import datetime
import collections

SELECTION_RE = re.compile(
    r'^\(Trang\s*([^,]*),\s*đoạn được chọn:\s*(.*)\)\s*\n?(.*)$', re.S
)


def parse_student_content(content):
    """Tách (trang, đoạn bôi đen, câu hỏi gõ tay) từ content thô của học viên."""
    m = SELECTION_RE.match(content)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return None, None, content.strip()


def to_vn_datetime(iso_str):
    dt = datetime.datetime.fromisoformat(iso_str)
    return dt + datetime.timedelta(hours=7)


def load_chatlog(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def build_turns(rows):
    """Ghép student+tutor cùng turn_id -> 1 dict record."""
    by_turn = collections.defaultdict(dict)
    for r in rows:
        by_turn[r['turn_id']][r['role']] = r

    turns = []
    for turn_id, d in by_turn.items():
        if 'student' not in d or 'tutor' not in d:
            continue  # turn lẻ, bỏ qua (rất hiếm theo data dictionary: turn_status luôn completed)
        s, t = d['student'], d['tutor']
        page, selection, question = parse_student_content(s['content'])
        turns.append({
            'turn_id': turn_id,
            'conversation_id': s['conversation_id'],
            'user_id': s['user_id'],
            'vn_time': to_vn_datetime(s['message_created_at']),
            'page': page,
            'selection': selection,
            'question': question,
            'tutor_content': t['content'],
            'move_used': t['move_used'],
            'citations': t['citations'],
            'rating': t['rating'],
        })
    turns.sort(key=lambda x: x['vn_time'])
    return turns


def group_by_day(turns):
    """date_str (YYYY-MM-DD, giờ VN) -> conversation_id -> [turn, ...] (đã sort theo thời gian).

    Trả về dict thường (không dùng defaultdict(lambda: ...)) — lambda lồng trong hàm
    không pickle được, sẽ vỡ st.cache_data ở dashboard.py.
    """
    by_day = {}
    for t in turns:
        date_str = t['vn_time'].strftime('%Y-%m-%d')
        by_day.setdefault(date_str, {}).setdefault(t['conversation_id'], []).append(t)
    return by_day


def list_available_days(turns):
    c = collections.Counter(t['vn_time'].strftime('%Y-%m-%d') for t in turns)
    return sorted(c.items())


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else \
        '../data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv'
    rows = load_chatlog(path)
    turns = build_turns(rows)
    print(f"Turns ghép cặp thành công: {len(turns)}")
    for d, n in list_available_days(turns):
        print(f"  {d}: {n} lượt")
