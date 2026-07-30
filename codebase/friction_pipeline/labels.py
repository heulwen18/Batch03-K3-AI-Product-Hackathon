import re
from collections import Counter, defaultdict

from .text import normalize, tokens, cosine


LABELS = ("student_stuck", "chat_cannot_help", "irrelevant_question")
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
    # The output contract is exclusive. Clear non-learning prompts take priority,
    # followed by evidence that the tutor could not help; all learning turns are
    # treated as student-stuck candidates.
    if not question or IRRELEVANT_RE.search(question):
        return "irrelevant_question"
    if tutor_failed(turn["tutor_text"]):
        return "chat_cannot_help"
    return "student_stuck"


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
