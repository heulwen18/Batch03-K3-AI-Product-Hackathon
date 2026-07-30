"""KHỐI 3 — UI dashboard cho giảng viên. Chỉ hiển thị/điều phối — không tự suy luận gì thêm.

Chạy: streamlit run dashboard.py   (từ bất kỳ đâu, path tự resolve theo vị trí file)
"""
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data" / "vlearn-pack"
CHATLOG_PATH = DATA_DIR / "chatlog" / "chat_history_anonymized_for_hackathon.csv"
TRANSCRIPT_DIR = DATA_DIR / "transcript"
MIN_SAMPLE_SIZE = 20  # dưới ngưỡng này -> "chưa đủ tin cậy" (đúng lớp chỗ khó ②, spec.md §6)

sys.path.insert(0, str(BASE_DIR))
from data_prep import load_chatlog, build_turns, group_by_day          # noqa: E402
from signals import build_day_cases, REPEAT_PAGE_THRESHOLD             # noqa: E402
from transcript_index import load_transcript_paragraphs                # noqa: E402
from classify_friction import classify_day                             # noqa: E402

st.set_page_config(page_title="Bản đồ Vướng Mắc Lớp", page_icon="🗺️", layout="wide")


@st.cache_resource
def load_all():
    rows = load_chatlog(str(CHATLOG_PATH))
    turns = build_turns(rows)
    by_day = group_by_day(turns)
    index = load_transcript_paragraphs(str(TRANSCRIPT_DIR))
    return by_day, index


by_day, transcript_idx = load_all()
days = sorted(by_day.keys())

st.title("🗺️ Bản đồ Vướng Mắc Lớp — Class Friction Map")
st.caption(
    "Prototype demo cho giảng viên/TA · Khối 1 = rule-based (không AI) · Khối 2 = lời gọi AI thật. "
    "Chi tiết kiến trúc: `codebase/README.md`."
)

with st.sidebar:
    st.header("Cấu hình")
    selected_date = st.selectbox("Chọn ngày học", days, index=len(days) - 1 if days else 0)
    dry_mode = st.radio(
        "Chế độ Khối 2",
        ["Dry-run (xem payload, không tốn quota)", "Gọi AI thật"],
        index=0,
    ) == "Dry-run (xem payload, không tốn quota)"
    api_key_input = st.text_input("GROQ_API_KEY (bỏ trống nếu đã có trong codebase/.env)", type="password")
    run_clicked = st.button("▶ Phân tích ngày này", type="primary", use_container_width=True)
    st.caption("Khối 1 (số liệu tổng quan bên dưới) luôn chạy tức thời, không cần bấm nút.")

st.subheader(f"Ngày {selected_date}")

# ---- Khối 1: luôn chạy, rẻ, không cần AI ----
day_report = build_day_cases(by_day[selected_date])
total = day_report["total_conversations"]
n_friction = day_report["n_friction_cases"]

c1, c2, c3 = st.columns(3)
c1.metric("Tổng hội thoại", total)
c2.metric("Có tín hiệu friction", n_friction)
c3.metric("Tỷ lệ", f"{(n_friction / max(total, 1) * 100):.0f}%")

st.markdown("**Breakdown 3 nhóm friction** *(Khối 1 — rule-based, số thật, không cần AI)*")
b = day_report["category_breakdown"]
cb1, cb2, cb3 = st.columns(3)
cb1.metric("🔧 Tutor Limitation", f"{b['tutor_limitation']['percent']}%", help="AI Tutor chưa hỗ trợ được: không tìm thấy tài liệu / trả lời chưa đúng câu hỏi")
cb2.metric("📖 Learning Difficulty", f"{b['learning_difficulty']['percent']}%", help="Học viên có dấu hiệu chưa hiểu: hỏi lại cùng khái niệm / cần giải thích nhiều lần")
cb3.metric("💬 Learning Intent Drift", f"{b['intent_drift']['percent']}%", help="Không tập trung vào mục tiêu học: chào hỏi / câu hỏi ngoài phạm vi")

if total < MIN_SAMPLE_SIZE:
    st.warning(
        f"⚠️ Ngày này chỉ có {total} hội thoại (< {MIN_SAMPLE_SIZE}) — mẫu quá nhỏ, "
        "kết quả % bên dưới có độ tin cậy thấp. Đây là hành vi mong muốn cho lớp chỗ khó "
        "② Mơ hồ/thiếu thông tin (spec.md §5-§6), không phải lỗi."
    )

if n_friction == 0:
    st.info("Không có hội thoại nào có tín hiệu friction trong ngày này — không cần gọi Khối 2.")
    st.stop()

# ---- Khối 2: chỉ chạy khi bấm nút (tốn quota nếu live) ----
if run_clicked:
    with st.spinner("Đang chạy Khối 2..."):
        try:
            payload, result = classify_day(
                selected_date, day_report, transcript_idx,
                api_key=api_key_input or None, dry_run=dry_mode,
            )
            st.session_state["payload"] = payload
            st.session_state["result"] = result
            st.session_state["dry"] = dry_mode
            st.session_state["date"] = selected_date
        except Exception as e:
            st.error(f"Lỗi khi gọi Khối 2: {e}")

payload = st.session_state.get("payload") if st.session_state.get("date") == selected_date else None
result = st.session_state.get("result") if st.session_state.get("date") == selected_date else None
was_dry = st.session_state.get("dry", True)

if payload is None:
    st.info("Bấm **▶ Phân tích ngày này** ở sidebar để chạy Khối 2.")
elif was_dry or result is None:
    st.warning(
        f"Đang ở chế độ **DRY-RUN** — chưa gọi AI thật (payload {len(str(payload))} ký tự, "
        f"{len(payload['clusters'])} cụm). Chuyển sang 'Gọi AI thật' + nhập API key để chạy thật."
    )
    with st.expander("Xem payload sẽ gửi cho model"):
        st.json(payload)
else:
    concepts = result.get("concepts", [])
    st.success(f"Đã phân tích — {len(concepts)} khái niệm học viên đang vướng trong ngày {selected_date}.")

    if result.get("low_confidence_note"):
        st.warning(f"Ghi chú độ tin cậy: {result['low_confidence_note']}")

    CATEGORY_LABEL = {
        "tutor_limitation": "🔧 Tutor Limitation",
        "learning_difficulty": "📖 Learning Difficulty",
        "intent_drift": "💬 Learning Intent Drift",
    }
    ROOT_CAUSE_LABEL = {"content_gap": "chưa dạy rõ (trong 6 buổi được cấp)", "retrieval_bug": "lỗi tìm kiếm của tutor"}

    for c in concepts:
        category = c.get("category", "")
        label = CATEGORY_LABEL.get(category, category)
        with st.expander(
            f"{label} · **{c['concept']}** — {c['percent_of_day']:.0f}% ({c['case_count']} hội thoại)"
        ):
            root_cause = c.get("root_cause", "khong_ap_dung")
            if category == "tutor_limitation" and root_cause in ROOT_CAUSE_LABEL:
                st.markdown(f"**Nguyên nhân cụ thể:** {ROOT_CAUSE_LABEL[root_cause]}")
            st.markdown(f"**Vì sao:** {c.get('cause_rationale', '')}")
            if c.get("example_quote"):
                st.markdown(f"**Ví dụ nguyên văn:** _{c['example_quote']}_")
            st.markdown(f"**Gợi ý hành động cho giảng viên/TA:** {c.get('suggested_action', '')}")

            st.caption("Case gốc liên quan (drill-down — không hiện danh tính học viên):")
            for tid, q in zip(c.get("example_turn_ids", []), c.get("example_quotes", [])):
                st.markdown(f"- `[{tid}]` *\"{q}\"*")

st.divider()
st.caption(
    "Non-goal (spec.md §4): không hiện `user_id`/danh tính học viên cụ thể — chỉ tổng hợp cấp lớp. "
    "Không tự sinh nội dung dạy lại — chỉ chỉ ra vướng ở đâu và vì sao."
)
