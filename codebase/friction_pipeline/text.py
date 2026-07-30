import math
import re
import unicodedata
from collections import Counter


STOPWORDS = {
    "a", "anh", "ban", "bi", "cac", "cai", "cho", "co", "cua", "da", "day",
    "de", "den", "duoc", "em", "gi", "giup", "hay", "hieu", "hoc", "hoi",
    "khong", "la", "lai", "lam", "minh", "mot", "nao", "nay", "nhu", "nhung",
    "noi", "o", "roi", "tai", "the", "thi", "toi", "trang", "trong", "tu",
    "va", "ve", "voi", "xin",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.]+", " ", text.lower())).strip()


SELECTED_RE = re.compile(r'^\(Trang\s+\d+,\s*đoạn được chọn:\s*"(.*?)"\)\s*', re.I | re.S)


def split_prompt(content: str):
    """Return typed question and selected passage as separate features."""
    content = content or ""
    match = SELECTED_RE.match(content)
    if not match:
        return content.strip(), ""
    return content[match.end():].strip(), match.group(1).strip()


def typed_question(content: str) -> str:
    return split_prompt(content)[0]


def tokens(text: str):
    return [t for t in normalize(text).split() if len(t) > 1 and t not in STOPWORDS]


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0.0) for key, value in a.items())
    na = math.sqrt(sum(value * value for value in a.values()))
    nb = math.sqrt(sum(value * value for value in b.values()))
    return dot / (na * nb) if na and nb else 0.0
