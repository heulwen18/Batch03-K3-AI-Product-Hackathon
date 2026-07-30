"""Index đơn giản (keyword overlap, không cần embedding) trên 700 đoạn transcript.

Dùng để: (a) kiểm tra 1 khái niệm có được giảng tường minh không,
         (b) đính kèm đoạn transcript liên quan làm bằng chứng cho Khối 2.
Không gọi AI — thuần rule-based, kiểm lại được bằng tay.
"""
import re
import glob
import unicodedata

PARA_RE = re.compile(r'\*\*\[(T\d\d-\d\d\d)\]\*\*\s*(.+?)(?=\n\n|\Z)', re.S)

STOPWORDS = set(
    'của và là các một trong cho về với những này khi thì được có nào như '
    'đoạn trang bôi đen giải thích tóm tắt tôi bạn cái gì không mình hay '
    'đó nó ở ra tại sao thế hãy đi nhé slide bài học nội dung chính hôm '
    'nay day'.split()
)


def normalize(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9\s]', ' ', s)


def load_transcript_paragraphs(transcript_dir):
    paras = []
    for f in sorted(glob.glob(f'{transcript_dir}/transcript-0*.md')):
        text = open(f, encoding='utf-8').read()
        for m in PARA_RE.finditer(text):
            code, body = m.group(1), re.sub(r'\s+', ' ', m.group(2))
            paras.append((code, normalize(body), body))
    return paras


def keywords(text, min_len=3):
    return set(w for w in normalize(text).split() if len(w) > min_len and w not in STOPWORDS)


def search(query, index, k=3):
    """Trả top-k đoạn khớp nhiều từ khoá nhất với query (không dấu, đã lọc stopword)."""
    q_kw = keywords(query)
    if len(q_kw) < 2:
        return []
    scored = []
    for code, norm_body, orig_body in index:
        body_kw = set(norm_body.split())
        overlap = len(q_kw & body_kw)
        if overlap:
            scored.append({
                'code': code,
                'match_ratio': overlap / len(q_kw),
                'overlap_count': overlap,
                'excerpt': orig_body[:220],
            })
    scored.sort(key=lambda x: (x['match_ratio'], x['overlap_count']), reverse=True)
    return scored[:k]


if __name__ == '__main__':
    idx = load_transcript_paragraphs('../data/vlearn-pack/transcript')
    print(f"Đoạn transcript đã index: {len(idx)}")
    for q in ["ReAct agent", "self attention transformer", "few-shot prompting"]:
        r = search(q, idx)
        print(f"\nQuery: {q!r} -> {len(r)} kết quả")
        for x in r:
            print(f"   [{x['code']}] match={x['match_ratio']:.0%} :: {x['excerpt'][:90]}")
