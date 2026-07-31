"""Helper dùng chung cho các trang trong app_pages/ — load data, nhãn, điểm rủi ro,
gom tuần, báo cáo tuần, cache kết quả AI. Không render UI ở module này (trừ các hàm render_* nhỏ).
"""
import json
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data" / "vlearn-pack"
CHATLOG_PATH = DATA_DIR / "chatlog" / "chat_history_anonymized_for_hackathon.csv"
TRANSCRIPT_DIR = DATA_DIR / "transcript"
RESULTS_DIR = BASE_DIR / "results"      # cache kết quả AI phân tích — mỗi phạm vi chỉ tốn 1 lời gọi
MIN_SAMPLE_SIZE = 20                     # dưới ngưỡng này -> cảnh báo "chưa đủ tin cậy"

# Ngưỡng mức độ (nhóm tự chọn, chỉ để sắp xếp/tô màu — không tự động ra quyết định)
SEVERITY_HIGH = 15.0
SEVERITY_MED = 7.0
CONV_RISK_HIGH = 8.0
CONV_RISK_MED = 4.0

import sys                                # noqa: E402
sys.path.insert(0, str(BASE_DIR))
from data_prep import load_chatlog, build_turns, group_by_day          # noqa: E402
from signals import build_day_cases, compute_conversation_signals, CATEGORIES  # noqa: E402
from transcript_index import load_transcript_paragraphs                # noqa: E402

CATEGORY_LABEL = {
    "tutor_limitation": "🔧 Tutor Limitation",
    "learning_difficulty": "📖 Learning Difficulty",
    "intent_drift": "💬 Off-topic / Drift",
}
NORMAL_LABEL = "✅ Normal / No issue"
ROOT_CAUSE_LABEL = {"content_gap": "chưa dạy rõ (trong các buổi được cấp)", "retrieval_bug": "lỗi tìm kiếm của tutor"}

CATEGORY_HELP = {
    "tutor_limitation": "AI Tutor chưa hỗ trợ được: không tìm thấy tài liệu / trả lời chưa đúng câu hỏi",
    "learning_difficulty": "Học viên có dấu hiệu chưa hiểu: hỏi lại cùng khái niệm / cần giải thích nhiều lần / tự nói 'không hiểu'",
    "intent_drift": "Không tập trung mục tiêu học: chào hỏi / câu hỏi ngoài phạm vi",
}

RISK_HELP = (
    "Điểm rủi ro CỦA HỘI THOẠI (không phải của học viên) = số lượt hỏi + số lần lặp trang nhiều nhất "
    "+ 2×(số lần AI phải cho đáp án trực tiếp) + 2×(số lần học viên tự nói 'không hiểu') "
    "+ 2 nếu rating cuối là 'down'. Công thức cố định, kiểm lại được bằng tay."
)


def severity_label(percent):
    if percent >= SEVERITY_HIGH:
        return "🔴 Cao"
    if percent >= SEVERITY_MED:
        return "🟠 Trung bình"
    return "🟢 Thấp"


def risk_score(signals):
    return (
        signals['n_turns']
        + signals['repeated_page_max']
        + signals['direct_answer_count'] * 2
        + signals.get('confusion_count', 0) * 2
        + (2 if signals['rating_down_quit'] else 0)
    )


def conversation_risk_label(score):
    if score >= CONV_RISK_HIGH:
        return "🔴 Cao"
    if score >= CONV_RISK_MED:
        return "🟠 Trung bình"
    return "🟢 Thấp"


@st.cache_resource
def load_all():
    rows = load_chatlog(str(CHATLOG_PATH))
    turns = build_turns(rows)
    by_day = group_by_day(turns)
    index = load_transcript_paragraphs(str(TRANSCRIPT_DIR))
    return by_day, index


# ---------------- Tuần học ----------------

def _week_key(date_str):
    y, w, _ = datetime.date.fromisoformat(date_str).isocalendar()
    return (y, w)


def weeks_of(days):
    """days (sorted) -> danh sách (label, [days]) theo tuần ISO, tuần mới nhất cuối cùng.
    Không giới hạn số buổi — data thêm tuần mới sẽ tự xuất hiện."""
    groups = {}
    for d in sorted(days):
        groups.setdefault(_week_key(d), []).append(d)
    out = []
    for key in sorted(groups):
        ds = groups[key]
        first = datetime.date.fromisoformat(ds[0]).strftime("%d/%m")
        last = datetime.date.fromisoformat(ds[-1]).strftime("%d/%m")
        out.append((f"Tuần {key[1]} · {first}–{last}", ds))
    return out


@st.cache_data(ttl=3600)
def build_week_report(_by_day, days):
    """Gộp báo cáo rule-based của nhiều ngày thành 1 báo cáo tuần (cùng khuôn dạng
    build_day_cases nên classify_day/build_clusters dùng lại được y nguyên)."""
    total, cases = 0, []
    cat = {c: 0 for c in CATEGORIES}
    per_day = {}
    for d in days:
        rep = build_day_cases(_by_day[d])
        per_day[d] = rep
        total += rep["total_conversations"]
        cases += rep["friction_cases"]
        for c in CATEGORIES:
            cat[c] += rep["category_breakdown"][c]["count"]
    return {
        "total_conversations": total,
        "friction_cases": cases,
        "n_friction_cases": len(cases),
        "category_breakdown": {
            c: {"count": cat[c], "percent": round(cat[c] / max(total, 1) * 100, 1)} for c in CATEGORIES
        },
        "per_day": per_day,
    }


def per_day_frame(week_report):
    """DataFrame ngày × (số hội thoại từng nhóm + Normal) cho biểu đồ."""
    rows = []
    for d, rep in week_report["per_day"].items():
        b = rep["category_breakdown"]
        rows.append({
            "Ngày": d[5:],  # mm-dd cho gọn trục
            CATEGORY_LABEL["learning_difficulty"]: b["learning_difficulty"]["count"],
            CATEGORY_LABEL["tutor_limitation"]: b["tutor_limitation"]["count"],
            CATEGORY_LABEL["intent_drift"]: b["intent_drift"]["count"],
            NORMAL_LABEL: rep["total_conversations"] - rep["n_friction_cases"],
        })
    return pd.DataFrame(rows).set_index("Ngày")


# ---------------- Cache kết quả AI (theo phạm vi: 1 ngày hoặc 1 tuần) ----------------

def _cache_path(scope_key):
    return RESULTS_DIR / f"khoi2_{scope_key}.json"


def save_ai_result(scope_key, payload, result):
    RESULTS_DIR.mkdir(exist_ok=True)
    _cache_path(scope_key).write_text(
        json.dumps({"payload": payload, "result": result}, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def load_ai_result(scope_key):
    path = _cache_path(scope_key)
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("payload"), data.get("result")
    except (json.JSONDecodeError, OSError):
        return None, None


def get_ai_state(scope_key):
    """(payload, result, from_cache) — ưu tiên kết quả trong phiên, sau đó file cache."""
    if st.session_state.get("ai_scope") == scope_key and st.session_state.get("ai_payload") is not None:
        return st.session_state["ai_payload"], st.session_state.get("ai_result"), False
    payload, result = load_ai_result(scope_key)
    if payload is not None and result is not None:
        return payload, result, True
    return None, None, False


def set_ai_state(scope_key, payload, result):
    st.session_state["ai_scope"] = scope_key
    st.session_state["ai_payload"] = payload
    st.session_state["ai_result"] = result
    if result is not None:
        save_ai_result(scope_key, payload, result)


# ---------------- Nguồn trích dẫn của tutor ----------------

def collect_sources(tool_log, k=4):
    best = {}
    for call in tool_log:
        for r in call["results"]:
            if r["code"] not in best or r["match_ratio"] > best[r["code"]]["match_ratio"]:
                best[r["code"]] = r
    return sorted(best.values(), key=lambda r: r["match_ratio"], reverse=True)[:k]


def render_sources(sources):
    if not sources:
        return
    with st.expander(f"📚 Nguồn đã tra cứu ({len(sources)} đoạn)"):
        for r in sources:
            st.markdown(f"**`[{r['code']}]`** · khớp {r['match_ratio']:.0%}")
            st.caption(r["excerpt"])
