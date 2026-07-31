"""Chat với AI Tutor — học viên hỏi đáp trên bài giảng hoặc file tự upload."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui_common import collect_sources, load_all, render_sources  # noqa: E402
from agent_tutor import build_system_prompt, format_question, run_turn, turn_to_case_format  # noqa: E402
from upload_index import build_upload_index  # noqa: E402

by_day, transcript_idx = load_all()

st.markdown("### 🎓 Chat với AI Tutor")


def _reset_chat_session():
    st.session_state["agent_history"] = []
    st.session_state["demo_turns"] = []
    st.session_state["turn_n"] = 0


with st.expander(
    "📎 Upload slide/tài liệu để hỏi đáp riêng (PDF / PPTX / TXT / MD)",
    expanded=not st.session_state.get("upload_index") and not st.session_state.get("demo_turns"),
):
    uploaded = st.file_uploader(
        "Chọn file — mỗi trang PDF hoặc mỗi slide PPTX sẽ là 1 đơn vị trích dẫn.",
        type=["pdf", "pptx", "txt", "md"], key="chat_upload",
    )
    if uploaded is not None:
        upload_key = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("upload_key") != upload_key:
            try:
                idx = build_upload_index(uploaded.name, uploaded.getvalue())
            except Exception as e:
                st.error(f"Không đọc được file: {e}")
                idx = None
            if idx is not None and not idx:
                st.warning("Không trích được văn bản nào từ file này — có thể slide toàn ảnh/scan (bản demo chưa hỗ trợ OCR).")
            elif idx:
                st.session_state["upload_index"] = idx
                st.session_state["upload_name"] = uploaded.name
                st.session_state["upload_key"] = upload_key
                _reset_chat_session()
                st.success(f"Đã đọc **{uploaded.name}** — {len(idx)} trang/đoạn. Câu hỏi bên dưới sẽ CHỈ dựa trên file này.")

    if st.session_state.get("upload_index"):
        uc1, uc2 = st.columns([3, 1])
        uc1.caption(f"📄 Đang hỏi đáp trên: **{st.session_state['upload_name']}** ({len(st.session_state['upload_index'])} trang/đoạn)")
        if uc2.button("❌ Bỏ file", width="stretch"):
            for k in ("upload_index", "upload_name", "upload_key"):
                st.session_state.pop(k, None)
            _reset_chat_session()
            st.rerun()

using_upload = bool(st.session_state.get("upload_index"))
active_index = st.session_state["upload_index"] if using_upload else transcript_idx
source_label = f"tài liệu bạn vừa upload ({st.session_state.get('upload_name')})" if using_upload else "các buổi giảng được cấp"

ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
if using_upload:
    page_input = ctrl1.text_input("Trang/slide đang xem (tuỳ chọn)", placeholder="vd 3", key="chat_page_input")
else:
    page_input = ctrl1.text_input("Trang đang xem (tuỳ chọn)", placeholder="vd 45", key="chat_page_input")
ctrl2.caption("Đang hỏi đáp trên")
ctrl2.write(f"📄 {st.session_state['upload_name']}" if using_upload else "📚 Bài giảng của khoá")
if ctrl3.button("🔄 Hội thoại mới", width="stretch"):
    _reset_chat_session()
    st.rerun()

if "agent_history" not in st.session_state:
    _reset_chat_session()

if not st.session_state["demo_turns"]:
    with st.chat_message("assistant"):
        if using_upload:
            st.write(f"Mình đã đọc xong **{st.session_state['upload_name']}**. Hỏi mình bất cứ điều gì về nội dung trong file này nhé!")
        else:
            st.write("Xin chào! Mình là VLearn Tutor. Bạn có thể upload slide riêng ở trên, nhập số trang đang xem, hoặc gửi câu hỏi tự do nhé!")

for t in st.session_state["demo_turns"]:
    with st.chat_message("user"):
        st.write(t["question"])
    with st.chat_message("assistant"):
        st.write(t["tutor_content"])
        render_sources(t.get("citations") or [])

user_q = st.chat_input("Nhập câu hỏi...")

if user_q:
    formatted = format_question(user_q, page_input or None)
    with st.chat_message("user"):
        st.write(user_q)
    with st.spinner("Đang tra cứu tài liệu..."):
        try:
            answer, tool_log, new_history = run_turn(
                active_index, st.session_state["agent_history"], formatted,
                system_prompt=build_system_prompt(source_label), source_label=source_label,
            )
        except Exception as e:
            st.error(f"Lỗi khi gọi AI Tutor: {e}\n\nCần GROQ_API_KEY hợp lệ trong codebase/.env.")
            st.stop()

    st.session_state["agent_history"] = new_history
    st.session_state["turn_n"] += 1
    turn_id = f"DEMO{st.session_state['turn_n']:03d}"
    sources = collect_sources(tool_log)
    demo_turn = turn_to_case_format(turn_id, page_input, user_q, answer)
    demo_turn["citations"] = sources
    st.session_state["demo_turns"].append(demo_turn)

    with st.chat_message("assistant"):
        st.write(answer)
        render_sources(sources)

if st.session_state["demo_turns"]:
    st.caption("💡 Hội thoại này xem lại được ở trang **Conversations** (mục 🧪 Phiên demo hiện tại).")
