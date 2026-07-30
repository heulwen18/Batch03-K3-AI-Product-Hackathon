"""APP TỔNG HỢP — 1 web Streamlit duy nhất, chạy local bằng 1 lệnh:

    streamlit run app.py

2 tab:
  🧑‍🎓 Chat với AI Tutor  — Agent A (ReAct/tool-calling), học viên chat trực tiếp
  📊 Dashboard Giảng viên/TA — Khối 1+2+3, thống kê học viên đang vướng chủ đề gì

Đây KHÔNG phải 2 sản phẩm khác nhau — tab Chat sinh ra hội thoại, tab Dashboard đọc lại
hội thoại (thật từ data pack, hoặc vừa chat xong ở tab kia) để phân loại + tổng hợp insight.
`dashboard.py` và `agent_demo_ui.py` vẫn chạy độc lập được (dùng khi cần demo 2 màn hình riêng),
nhưng `app.py` là entry point chính — dùng file này khi cần 1 web duy nhất.
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
from signals import build_day_cases                                    # noqa: E402
from transcript_index import load_transcript_paragraphs                # noqa: E402
from classify_friction import classify_day                             # noqa: E402
from agent_tutor import run_turn, format_question, turn_to_case_format  # noqa: E402

st.set_page_config(page_title="VLearn AI Tutor & Insight", page_icon="🎓", layout="wide")

CATEGORY_LABEL = {
    "tutor_limitation": "🔧 Tutor Limitation",
    "learning_difficulty": "📖 Learning Difficulty",
    "intent_drift": "💬 Learning Intent Drift",
}
ROOT_CAUSE_LABEL = {"content_gap": "chưa dạy rõ (trong 6 buổi được cấp)", "retrieval_bug": "lỗi tìm kiếm của tutor"}


@st.cache_resource
def load_all():
    rows = load_chatlog(str(CHATLOG_PATH))
    turns = build_turns(rows)
    by_day = group_by_day(turns)
    index = load_transcript_paragraphs(str(TRANSCRIPT_DIR))
    return by_day, index


def render_chat_tab(transcript_idx, api_key_input):
    st.markdown(
        "<div style='padding:14px 18px;border-radius:14px;background:rgba(120,120,255,0.08);"
        "border:1px solid rgba(120,120,255,0.25);margin-bottom:12px;'>"
        "<b>🎓 VLearn Tutor</b> · <span style='opacity:0.7'>Trợ lý học theo ngữ cảnh (demo Agent A — ReAct/tool-calling)</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    page_input = ctrl1.text_input("Trang đang xem (tuỳ chọn — mô phỏng bôi đen slide)", placeholder="vd 45", key="chat_page_input")
    ctrl2.caption("Ngữ cảnh hiện tại")
    ctrl2.write(f"Slide trang: {page_input}" if page_input else "Slide trang: (chưa chọn)")
    if ctrl3.button("🔄 Hội thoại mới", use_container_width=True):
        st.session_state["agent_history"] = []
        st.session_state["demo_turns"] = []
        st.session_state["turn_n"] = 0
        st.session_state.pop("last_classify", None)
        st.rerun()

    if "agent_history" not in st.session_state:
        st.session_state["agent_history"] = []
        st.session_state["demo_turns"] = []
        st.session_state["turn_n"] = 0

    if not st.session_state["demo_turns"]:
        with st.chat_message("assistant"):
            st.write("Xin chào! Mình là VLearn Tutor. Bạn có thể bôi đen một đoạn trên slide (nhập số trang ở trên) để hỏi, hoặc gửi câu hỏi tự do nhé!")

    for t in st.session_state["demo_turns"]:
        with st.chat_message("user"):
            st.write(t["question"])
        with st.chat_message("assistant"):
            st.write(t["tutor_content"])

    user_q = st.chat_input("Nhập câu hỏi hoặc bôi đen tài liệu...")

    if user_q:
        formatted = format_question(user_q, page_input or None)
        with st.chat_message("user"):
            st.write(user_q)
        with st.spinner("Agent đang tra cứu transcript..."):
            try:
                answer, tool_log, new_history = run_turn(
                    transcript_idx, st.session_state["agent_history"], formatted,
                    api_key=api_key_input or None,
                )
            except Exception as e:
                st.error(f"Lỗi khi gọi Agent A: {e}\n\nCần GROQ_API_KEY hợp lệ (nhập ở sidebar hoặc đặt trong codebase/.env).")
                st.stop()

        st.session_state["agent_history"] = new_history
        st.session_state["turn_n"] += 1
        turn_id = f"DEMO{st.session_state['turn_n']:03d}"
        st.session_state["demo_turns"].append(turn_to_case_format(turn_id, page_input, user_q, answer))

        with st.chat_message("assistant"):
            st.write(answer)
            if tool_log:
                with st.expander(f"🔍 Agent đã tra cứu {len(tool_log)} lần (debug)"):
                    for call in tool_log:
                        st.caption(f"query: {call['query']!r}")
                        for r in call["results"]:
                            st.caption(f"   [{r['code']}] match={r['match_ratio']:.0%} — {r['excerpt'][:100]}")

    demo_turns = st.session_state["demo_turns"]
    if demo_turns:
        st.divider()
        with st.expander("🔎 Nối vào Khối 1+2 — phân loại hội thoại demo này (để kiểm tra pipeline)"):
            fake_day = {"DEMO-CONV": demo_turns}
            demo_report = build_day_cases(fake_day)

            if demo_report["n_friction_cases"] == 0:
                st.info("Hội thoại này chưa có tín hiệu friction nào (Khối 1) — hỏi thêm vài câu, hoặc hỏi lại cùng 1 khái niệm/trang 3 lần để kích hoạt tín hiệu Learning Difficulty.")
            else:
                case = demo_report["friction_cases"][0]
                st.write(f"**Khối 1 (rule-based) đã gắn nhóm:** `{case['signals']['primary_category']}` — categories: {case['signals']['categories']}")

                dry = st.checkbox("Dry-run (không tốn quota, chỉ xem payload)", value=True, key="chat_dry")
                if st.button("▶ Phân loại qua Khối 2 (AI thật)", type="primary", key="chat_classify_btn"):
                    with st.spinner("Đang gọi Khối 2..."):
                        try:
                            payload, result = classify_day("DEMO", demo_report, transcript_idx, api_key=api_key_input or None, dry_run=dry)
                            st.session_state["last_classify"] = (payload, result, dry)
                        except Exception as e:
                            st.error(f"Lỗi khi gọi Khối 2: {e}")

                if "last_classify" in st.session_state:
                    payload, result, was_dry = st.session_state["last_classify"]
                    if was_dry or result is None:
                        st.warning("Dry-run — chưa gọi AI thật.")
                        st.json(payload)
                    else:
                        st.success("Khối 2 đã phân loại:")
                        st.json(result)


def render_dashboard_tab(by_day, transcript_idx, api_key_input):
    days = sorted(by_day.keys())
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    selected_date = ctrl1.selectbox("Chọn ngày học", days, index=len(days) - 1 if days else 0, key="dash_date")
    dry_mode = ctrl2.radio(
        "Chế độ Khối 2", ["Dry-run (xem payload, không tốn quota)", "Gọi AI thật"], index=0, key="dash_dry",
    ) == "Dry-run (xem payload, không tốn quota)"
    ctrl3.write("")
    run_clicked = ctrl3.button("▶ Phân tích", type="primary", use_container_width=True, key="dash_run")

    st.subheader(f"Ngày {selected_date}")

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
        return

    if run_clicked:
        with st.spinner("Đang chạy Khối 2..."):
            try:
                payload, result = classify_day(selected_date, day_report, transcript_idx, api_key=api_key_input or None, dry_run=dry_mode)
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
        st.info("Bấm **▶ Phân tích** ở trên để chạy Khối 2.")
        return
    if was_dry or result is None:
        st.warning(
            f"Đang ở chế độ **DRY-RUN** — chưa gọi AI thật (payload {len(str(payload))} ký tự, "
            f"{len(payload['clusters'])} cụm). Chuyển sang 'Gọi AI thật' + nhập API key để chạy thật."
        )
        with st.expander("Xem payload sẽ gửi cho model"):
            st.json(payload)
        return

    concepts = result.get("concepts", [])
    st.success(f"Đã phân tích — {len(concepts)} khái niệm học viên đang vướng trong ngày {selected_date}.")
    if result.get("low_confidence_note"):
        st.warning(f"Ghi chú độ tin cậy: {result['low_confidence_note']}")

    for c in concepts:
        category = c.get("category", "")
        label = CATEGORY_LABEL.get(category, category)
        with st.expander(f"{label} · **{c['concept']}** — {c['percent_of_day']:.0f}% ({c['case_count']} hội thoại)"):
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


by_day, transcript_idx = load_all()

st.title("🎓 VLearn — AI Tutor & Class Insight")
st.caption(
    "1 web local · Tab 1: học viên chat với AI Tutor (Agent A, demo) · Tab 2: giảng viên/TA xem "
    "thống kê học viên đang vướng chủ đề gì (Khối 1+2+3, \"Bản đồ Vướng Mắc Lớp\" — spec.md §4)."
)

with st.sidebar:
    st.header("Cấu hình chung")
    api_key_input = st.text_input("GROQ_API_KEY (bỏ trống nếu đã có trong codebase/.env)", type="password")
    st.caption("Dùng chung cho cả 2 tab — không cần nhập lại.")

tab_chat, tab_dashboard = st.tabs(["🧑‍🎓 Chat với AI Tutor (học viên)", "📊 Dashboard Giảng viên/TA"])

with tab_chat:
    render_chat_tab(transcript_idx, api_key_input)

with tab_dashboard:
    render_dashboard_tab(by_day, transcript_idx, api_key_input)
