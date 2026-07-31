"""Màn hình phụ cho DEMO LIVE (Nhịp 2) — đóng vai học viên chat với Agent A (ReAct/tool-calling).

KHÔNG phải sản phẩm được chấm — chỉ để sinh hội thoại sống, sau đó nối vào ĐÚNG Khối 1+2 đã build
(signals.py / classify_friction.py) để chứng minh cả pipeline hoạt động end-to-end với input mới.

Chạy: streamlit run agent_demo_ui.py --server.port 8502   (chạy song song dashboard.py ở nhịp 1)
"""
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
TRANSCRIPT_DIR = BASE_DIR.parent / "data" / "vlearn-pack" / "transcript"

sys.path.insert(0, str(BASE_DIR))
from transcript_index import load_transcript_paragraphs          # noqa: E402
from agent_tutor import run_turn, format_question, turn_to_case_format  # noqa: E402
from signals import build_day_cases                              # noqa: E402
from classify_friction import classify_day                       # noqa: E402

st.set_page_config(page_title="Agent A — Demo Tutor", page_icon="🧑‍🎓", layout="wide")


@st.cache_resource
def load_index():
    return load_transcript_paragraphs(str(TRANSCRIPT_DIR))


transcript_idx = load_index()

st.title("🧑‍🎓 Agent A — Demo Tutor (ReAct/tool-calling)")
st.caption(
    "Đóng vai học viên chat live. Agent này KHÔNG phải tính năng được chấm — chỉ sinh hội thoại "
    "sống để nối vào Khối 1+2 (bên `dashboard.py`), đúng như thiết kế demo 2 nhịp trong spec.md."
)

with st.sidebar:
    st.header("Cấu hình")
    st.caption("GROQ_API_KEY đọc từ `codebase/.env` trên server — không nhập khoá trên giao diện để tránh lộ khoá.")
    page_input = st.text_input("Trang đang xem (tuỳ chọn — mô phỏng bôi đen slide)", placeholder="vd 45")
    if st.button("🔄 Bắt đầu hội thoại mới", use_container_width=True):
        st.session_state["agent_history"] = []
        st.session_state["demo_turns"] = []
        st.session_state["turn_n"] = 0
        st.session_state.pop("last_classify", None)
        st.rerun()

if "agent_history" not in st.session_state:
    st.session_state["agent_history"] = []
    st.session_state["demo_turns"] = []
    st.session_state["turn_n"] = 0

for t in st.session_state["demo_turns"]:
    with st.chat_message("user"):
        st.write(t["question"])
    with st.chat_message("assistant"):
        st.write(t["tutor_content"])

user_q = st.chat_input("Gõ câu hỏi như học viên đang chat với tutor...")

if user_q:
    formatted = format_question(user_q, page_input or None)
    with st.chat_message("user"):
        st.write(user_q)
    with st.spinner("Agent đang tra cứu transcript..."):
        try:
            answer, tool_log, new_history = run_turn(
                transcript_idx, st.session_state["agent_history"], formatted,
            )
        except Exception as e:
            st.error(f"Lỗi khi gọi Agent A: {e}\n\nCần GROQ_API_KEY hợp lệ trong codebase/.env.")
            st.stop()

    st.session_state["agent_history"] = new_history
    st.session_state["turn_n"] += 1
    turn_id = f"DEMO{st.session_state['turn_n']:03d}"
    st.session_state["demo_turns"].append(
        turn_to_case_format(turn_id, page_input, user_q, answer)
    )

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
    st.subheader("Nối vào Khối 1+2 — phân loại hội thoại demo này")

    fake_day = {"DEMO-CONV": demo_turns}
    demo_report = build_day_cases(fake_day)

    if demo_report["n_friction_cases"] == 0:
        st.info("Hội thoại này chưa có tín hiệu friction nào (Khối 1) — hỏi thêm vài câu, hoặc thử hỏi lại cùng 1 khái niệm/trang 3 lần để kích hoạt tín hiệu Learning Difficulty.")
    else:
        case = demo_report["friction_cases"][0]
        st.write(f"**Khối 1 (rule-based) đã gắn nhóm:** `{case['signals']['primary_category']}` "
                 f"— categories: {case['signals']['categories']}")

        run_live = st.button("▶ Phân loại qua Khối 2 (AI thật)", type="primary")
        dry = st.checkbox("Dry-run (không tốn quota, chỉ xem payload)", value=True)

        if run_live:
            with st.spinner("Đang gọi Khối 2..."):
                try:
                    payload, result = classify_day(
                        "DEMO", demo_report, transcript_idx,
                        dry_run=dry,
                    )
                    st.session_state["last_classify"] = (payload, result, dry)
                except Exception as e:
                    st.error(f"Lỗi khi gọi Khối 2: {e}")

        if "last_classify" in st.session_state:
            payload, result, was_dry = st.session_state["last_classify"]
            if was_dry or result is None:
                st.warning("Dry-run — chưa gọi AI thật.")
                with st.expander("Xem payload"):
                    st.json(payload)
            else:
                st.success("Khối 2 đã phân loại:")
                st.json(result)

st.divider()
st.caption(
    "Lưu ý: hội thoại demo này CHỈ tồn tại trong phiên hiện tại, không lưu vào data pack thật, "
    "không ảnh hưởng dashboard giảng viên ở `dashboard.py`."
)
