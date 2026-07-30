import re
from collections import Counter, defaultdict

from .text import normalize, tokens, cosine


LABELS = ("learning_difficulty", "tutor_limitation", "off_topic", "normal")
RETRIEVAL_RE = re.compile(
    r"(?:kh[oô]ng (?:th[ểe] )?t[iì]m th[ấa]y|ch[ưư]a t[iì]m th[ấa]y|"
    r"kh[oô]ng th[ấa]y|kh[oô]ng (?:th[ểe] )?truy (?:c[ậa]p|xu[ấa]t)|ch[ưư]a truy c[ậa]p|"
    r"kh[oô]ng c[oó] (?:n[oộ]i dung|th[oô]ng tin|t[aà]i li[eệ]u)|kh[oô]ng [đd][ềe] c[ậa]p|"
    r"ch[ưư]a c[oó] th[oô]ng tin|kh[oô]ng kh[ớo]p)", re.I)
CONFUSION_RE = re.compile(r"\b(khong hieu|chua hieu|la gi|nghia la gi|giai thich|vi sao|tai sao|khac nhau)\b")
IRRELEVANT_RE = re.compile(
    r"^(?:hi|hello|alo|test|ok|thanks|cam on|chao ban|bro)[.! ]*$|"
    r"\b(?:dep trai|xinh gai|ke chuyen cuoi|model cua hang nao|may la ai|ban la ai)\b"
)


TOPICS = {
    "agent / ReAct": ("agent", "react", "agentic"),
    "RAG / retrieval": ("rag", "retrieval", "truy xuat", "tim kiem tai lieu"),
    "prompt / context": ("prompt", "context", "ngu canh", "system prompt"),
    "JTBD / user problem": ("jtbd", "job to be done", "pain point", "problem statement", "van de nguoi dung"),
    "evaluation": ("eval", "evaluation", "golden set", "quality bar", "danh gia"),
    "AI model / LLM": ("llm", "mo hinh", "model", "token", "transformer"),
    "automation / workflow": ("automation", "workflow", "quy trinh", "augment"),
}


def tutor_failed(text):
    return bool(RETRIEVAL_RE.search(text or ""))


def seed_label(turn):
    question = normalize(turn["student_text"])
    # Off-topic prompts and tutor failures override learning-signal classification.
    if not question or IRRELEVANT_RE.search(question):
        return "off_topic"
    if tutor_failed(turn["tutor_text"]):
        return "tutor_limitation"
    if turn.get("repeated_question") or CONFUSION_RE.search(question) or turn["move_used"] in {"give_direct_answer", "give_hint"}:
        return "learning_difficulty"
    return "normal"


def topic_for(text):
    normalized = normalize(text)
    scores = {topic: sum(1 for key in keys if key in normalized) for topic, keys in TOPICS.items()}
    topic, score = max(scores.items(), key=lambda item: item[1])
    if score:
        return topic
    candidates = [t for t in tokens(text) if len(t) >= 4]
    return " ".join(candidates[:3]) if candidates else "other / unclear"


def add_repetition_signals(turns, threshold=0.48):
    conversations = defaultdict(list)
    for turn in turns:
        conversations[turn["conversation_id"]].append(turn)
    for items in conversations.values():
        previous = []
        for turn in items:
            vector = Counter(tokens(turn["student_text"]))
            turn["repeated_question"] = any(cosine(vector, old) >= threshold for old in previous)
            previous.append(vector)
    return turns
