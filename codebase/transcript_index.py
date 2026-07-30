"""Index đơn giản (không cần embedding) trên 700 đoạn transcript.

Dùng để: (a) kiểm tra 1 khái niệm có được giảng tường minh không,
         (b) đính kèm đoạn transcript liên quan làm bằng chứng cho Khối 2.
Không gọi AI — thuần rule-based, kiểm lại được bằng tay.

Xếp hạng bằng BM25 (tự cài, thuần Python, không thêm dependency): từ hiếm/đặc trưng
("transformer", "react") được ưu tiên hơn từ phổ biến — chính xác hơn hẳn đếm từ trùng thô.
`match_ratio` (tỷ lệ từ khoá của câu hỏi xuất hiện trong đoạn) vẫn được TRẢ VỀ NGUYÊN NGHĨA CŨ
vì Khối 2 (RETRIEVAL_BUG_THRESHOLD) và prompt Agent A đang dựa vào thang 0-1 này — BM25 chỉ
quyết định THỨ TỰ kết quả, không đổi ngưỡng nào ở downstream.
"""
import re
import glob
import math
import collections
import unicodedata

# Tham số BM25 chuẩn (Robertson) — không tự chế số, kiểm lại được với mọi tài liệu IR.
BM25_K1 = 1.5
BM25_B = 0.75

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
    """Trả top-k đoạn liên quan nhất với query (không dấu, đã lọc stopword).

    Thứ tự = điểm BM25 (từ hiếm được trọng số cao hơn). match_ratio giữ nguyên nghĩa cũ:
    tỷ lệ từ khoá của query có mặt trong đoạn (0-1) — downstream không cần đổi gì.
    """
    q_kw = keywords(query)
    if len(q_kw) < 2:
        return []

    doc_tokens = [collections.Counter(norm_body.split()) for _, norm_body, _ in index]
    n_docs = len(index)
    if n_docs == 0:
        return []
    avg_len = sum(sum(c.values()) for c in doc_tokens) / n_docs

    # document frequency chỉ cho từ trong query — 1 lượt duyệt, O(n_docs) mỗi lần search
    df = {t: sum(1 for c in doc_tokens if t in c) for t in q_kw}
    idf = {t: math.log((n_docs - df[t] + 0.5) / (df[t] + 0.5) + 1) for t in q_kw}

    scored = []
    for (code, _, orig_body), counts in zip(index, doc_tokens):
        overlap = sum(1 for t in q_kw if t in counts)
        if not overlap:
            continue
        doc_len = sum(counts.values())
        bm25 = sum(
            idf[t] * counts[t] * (BM25_K1 + 1)
            / (counts[t] + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / max(avg_len, 1)))
            for t in q_kw if t in counts
        )
        scored.append({
            'code': code,
            'match_ratio': overlap / len(q_kw),
            'overlap_count': overlap,
            'bm25_score': round(bm25, 3),
            'excerpt': orig_body[:220],
        })
    scored.sort(key=lambda x: x['bm25_score'], reverse=True)
    return scored[:k]


if __name__ == '__main__':
    idx = load_transcript_paragraphs('../data/vlearn-pack/transcript')
    print(f"Đoạn transcript đã index: {len(idx)}")
    for q in ["ReAct agent", "self attention transformer", "few-shot prompting"]:
        r = search(q, idx)
        print(f"\nQuery: {q!r} -> {len(r)} kết quả")
        for x in r:
            print(f"   [{x['code']}] match={x['match_ratio']:.0%} :: {x['excerpt'][:90]}")
