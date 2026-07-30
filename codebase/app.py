"""APP TỔNG HỢP — 1 web Streamlit duy nhất, chạy local bằng 1 lệnh:

    streamlit run app.py

3 tab:
  🧑‍🎓 Chat với AI Tutor   — Agent A (ReAct/tool-calling), học viên chat trực tiếp
  📊 Dashboard Giảng viên/TA — thống kê học viên đang vướng chủ đề gì (đếm rule-based
                              + AI đặt tên chủ đề/gợi ý hành động)
  🗂️ Nhật ký hội thoại      — đọc nguyên văn từng hội thoại + phân tích tín hiệu

Đây KHÔNG phải các sản phẩm khác nhau — tab Chat sinh ra hội thoại, tab Dashboard/Nhật ký đọc
lại hội thoại (thật từ data pack, hoặc vừa chat xong ở tab kia) để phân loại + tổng hợp insight.
`dashboard.py` và `agent_demo_ui.py` vẫn chạy độc lập được (dùng khi cần demo 2 màn hình riêng),
nhưng `app.py` là entry point chính — dùng file này khi cần 1 web duy nhất.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data" / "vlearn-pack"
CHATLOG_PATH = DATA_DIR / "chatlog" / "chat_history_anonymized_for_hackathon.csv"
TRANSCRIPT_DIR = DATA_DIR / "transcript"
RESULTS_DIR = BASE_DIR / "results"  # cache kết quả AI phân tích theo ngày — mỗi ngày chỉ tốn 1 lời gọi AI
MIN_SAMPLE_SIZE = 20  # dưới ngưỡng này -> "chưa đủ tin cậy" (đúng lớp chỗ khó ②, spec.md §6)

# Ngưỡng mức độ nghiêm trọng theo % hội thoại/ngày bị ảnh hưởng — nhóm tự chọn, có thể chỉnh,
# KHÔNG phải chuẩn tuyệt đối. Chỉ để sắp xếp/tô màu, không dùng để tự động ra quyết định.
SEVERITY_HIGH = 15.0
SEVERITY_MED = 7.0

# Ngưỡng điểm rủi ro CỦA 1 HỘI THOẠI (cùng công thức risk_score() bên dưới) — dùng riêng cho tab
# "Nhật ký hội thoại" để tô màu Mức độ trong bảng liệt kê. Nhóm tự chọn, chỉ để sắp xếp/tô màu.
CONV_RISK_HIGH = 8.0
CONV_RISK_MED = 4.0

sys.path.insert(0, str(BASE_DIR))
from data_prep import load_chatlog, build_turns, group_by_day          # noqa: E402
from signals import build_day_cases, compute_conversation_signals      # noqa: E402
from transcript_index import load_transcript_paragraphs                # noqa: E402
from classify_friction import classify_day, build_clusters             # noqa: E402
from agent_tutor import run_turn, format_question, turn_to_case_format, build_system_prompt  # noqa: E402
from upload_index import build_upload_index                            # noqa: E402

st.set_page_config(page_title="VLearn AI Tutor & Insight", page_icon="🎓", layout="wide")

CATEGORY_LABEL = {
    "tutor_limitation": "🔧 Tutor Limitation",
    "learning_difficulty": "📖 Learning Difficulty",
    "intent_drift": "💬 Learning Intent Drift",
}
ROOT_CAUSE_LABEL = {"content_gap": "chưa dạy rõ (trong 6 buổi được cấp)", "retrieval_bug": "lỗi tìm kiếm của tutor"}


def severity_label(percent_of_day):
    """Ngưỡng cố định, kiểm lại được — không phải điểm số AI đoán (spec.md nguyên tắc rule-based)."""
    if percent_of_day >= SEVERITY_HIGH:
        return "🔴 Cao"
    if percent_of_day >= SEVERITY_MED:
        return "🟠 Trung bình"
    return "🟢 Thấp"


def risk_score(signals):
    """Điểm rủi ro CỦA HỘI THOẠI (không phải của học viên) — 100% rule-based,
    công thức cộng tuyến tính đơn giản để có thể kiểm lại bằng tay:
      số lượt hỏi + số lần lặp trang nhiều nhất + 2×(số lần AI phải cho đáp án trực tiếp)
      + 2×(số lần học viên tự nói "không hiểu") + 2 nếu rating cuối cùng là 'down'.
    Dùng để giảng viên biết hội thoại nào đáng xem trước, KHÔNG dùng để xếp hạng/gắn nhãn học viên.
    """
    return (
        signals['n_turns']
        + signals['repeated_page_max']
        + signals['direct_answer_count'] * 2
        + signals.get('confusion_count', 0) * 2
        + (2 if signals['rating_down_quit'] else 0)
    )


def conversation_risk_label(score):
    """Ngưỡng cố định (CONV_RISK_HIGH/MED) — chỉ để tô màu Mức độ trong Nhật ký hội thoại,
    dùng cùng công thức risk_score() nên luôn kiểm lại được bằng tay."""
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


def _khoi2_cache_path(date):
    return RESULTS_DIR / f"khoi2_{date}.json"


def save_khoi2_result(date, payload, result):
    """Lưu kết quả AI phân tích ra file — F5/khởi động lại app không mất, không tốn quota gọi lại."""
    RESULTS_DIR.mkdir(exist_ok=True)
    _khoi2_cache_path(date).write_text(
        json.dumps({"payload": payload, "result": result}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_khoi2_result(date):
    """Đọc kết quả AI phân tích đã lưu của 1 ngày. Trả về (payload, result) hoặc (None, None)."""
    path = _khoi2_cache_path(date)
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("payload"), data.get("result")
    except (json.JSONDecodeError, OSError):
        return None, None


def get_khoi2_state(selected_date):
    """(payload, result, from_cache) — ưu tiên kết quả AI trong phiên hiện tại, sau đó tới file cache."""
    if st.session_state.get("date") == selected_date and st.session_state.get("payload") is not None:
        return st.session_state["payload"], st.session_state.get("result"), False
    payload, result = load_khoi2_result(selected_date)
    if payload is not None and result is not None:
        return payload, result, True
    return None, None, False


def _collect_sources(tool_log, k=4):
    """Gom kết quả tra cứu của 1 lượt agent thành danh sách nguồn duy nhất (dedup theo mã đoạn,
    giữ match cao nhất) — để hiển thị 'Nguồn đã tra cứu' dưới câu trả lời."""
    best = {}
    for call in tool_log:
        for r in call["results"]:
            if r["code"] not in best or r["match_ratio"] > best[r["code"]]["match_ratio"]:
                best[r["code"]] = r
    return sorted(best.values(), key=lambda r: r["match_ratio"], reverse=True)[:k]


def _render_sources(sources):
    if not sources:
        return
    with st.expander(f"📚 Nguồn đã tra cứu ({len(sources)} đoạn)"):
        for r in sources:
            st.markdown(f"**`[{r['code']}]`** · khớp {r['match_ratio']:.0%}")
            st.caption(r["excerpt"])


def _reset_chat_session():
    st.session_state["agent_history"] = []
    st.session_state["demo_turns"] = []
    st.session_state["turn_n"] = 0


def render_chat_tab(transcript_idx):
    st.markdown(
        "<div style='padding:14px 18px;border-radius:14px;background:rgba(120,120,255,0.08);"
        "border:1px solid rgba(120,120,255,0.25);margin-bottom:12px;'>"
        "<b>🎓 VLearn Tutor</b> · <span style='opacity:0.7'>Trợ lý học theo ngữ cảnh (demo Agent A — ReAct/tool-calling)</span>"
        "</div>",
        unsafe_allow_html=True,
    )

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
                    st.warning(
                        "Không trích được văn bản nào từ file này — có thể slide toàn ảnh/scan "
                        "(chưa hỗ trợ OCR trong bản demo này)."
                    )
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
                st.session_state.pop("upload_index", None)
                st.session_state.pop("upload_name", None)
                st.session_state.pop("upload_key", None)
                _reset_chat_session()
                st.rerun()

    using_upload = bool(st.session_state.get("upload_index"))
    active_index = st.session_state["upload_index"] if using_upload else transcript_idx
    source_label = f"tài liệu bạn vừa upload ({st.session_state.get('upload_name')})" if using_upload else "6 buổi giảng được cấp"

    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    if using_upload:
        ctrl1.caption("Trang/slide (tuỳ chọn — vd 3 để nhấn mạnh đang hỏi về trang đó)")
        page_input = ctrl1.text_input("Trang/slide", placeholder="vd 3", key="chat_page_input", label_visibility="collapsed")
    else:
        page_input = ctrl1.text_input("Trang đang xem (tuỳ chọn — mô phỏng bôi đen slide)", placeholder="vd 45", key="chat_page_input")
    ctrl2.caption("Đang hỏi đáp trên")
    ctrl2.write(f"📄 {st.session_state['upload_name']}" if using_upload else "📚 6 buổi giảng mẫu (data pack)")
    if ctrl3.button("🔄 Hội thoại mới", width="stretch"):
        _reset_chat_session()
        st.rerun()

    if "agent_history" not in st.session_state:
        st.session_state["agent_history"] = []
        st.session_state["demo_turns"] = []
        st.session_state["turn_n"] = 0

    if not st.session_state["demo_turns"]:
        with st.chat_message("assistant"):
            if using_upload:
                st.write(f"Mình đã đọc xong **{st.session_state['upload_name']}**. Hỏi mình bất cứ điều gì về nội dung trong file này nhé!")
            else:
                st.write("Xin chào! Mình là VLearn Tutor. Bạn có thể upload slide riêng ở trên, hoặc bôi đen một đoạn trên slide (nhập số trang ở trên) để hỏi, hoặc gửi câu hỏi tự do nhé!")

    for t in st.session_state["demo_turns"]:
        with st.chat_message("user"):
            st.write(t["question"])
        with st.chat_message("assistant"):
            st.write(t["tutor_content"])
            _render_sources(t.get("citations") or [])

    user_q = st.chat_input("Nhập câu hỏi hoặc bôi đen tài liệu...")

    if user_q:
        formatted = format_question(user_q, page_input or None)
        with st.chat_message("user"):
            st.write(user_q)
        with st.spinner("Agent đang tra cứu tài liệu..."):
            try:
                answer, tool_log, new_history = run_turn(
                    active_index, st.session_state["agent_history"], formatted,
                    system_prompt=build_system_prompt(source_label),
                )
            except Exception as e:
                st.error(f"Lỗi khi gọi Agent A: {e}\n\nCần GROQ_API_KEY hợp lệ trong codebase/.env.")
                st.stop()

        st.session_state["agent_history"] = new_history
        st.session_state["turn_n"] += 1
        turn_id = f"DEMO{st.session_state['turn_n']:03d}"
        sources = _collect_sources(tool_log)
        demo_turn = turn_to_case_format(turn_id, page_input, user_q, answer)
        demo_turn["citations"] = sources
        st.session_state["demo_turns"].append(demo_turn)

        with st.chat_message("assistant"):
            st.write(answer)
            _render_sources(sources)

@st.cache_data(ttl=3600)
def build_trend_frame(_by_day, day_keys):
    """% từng nhóm vướng mắc theo ngày — rule-based, tính 1 lần rồi cache.
    day_keys truyền riêng làm cache key (nội dung _by_day không đổi trong 1 phiên chạy)."""
    rows = []
    for d in day_keys:
        rep = build_day_cases(_by_day[d])
        b = rep["category_breakdown"]
        rows.append({
            "Ngày": d,
            "🔧 Tutor Limitation": b["tutor_limitation"]["percent"],
            "📖 Learning Difficulty": b["learning_difficulty"]["percent"],
            "💬 Intent Drift": b["intent_drift"]["percent"],
            "Tổng hội thoại": rep["total_conversations"],
        })
    return pd.DataFrame(rows).set_index("Ngày")


def render_dashboard_tab(by_day, transcript_idx):
    days = sorted(by_day.keys())

    st.markdown("**📈 Xu hướng vướng mắc theo ngày** *(đếm rule-based trên toàn bộ lịch sử — không dùng AI)*")
    trend_df = build_trend_frame(by_day, tuple(days))
    tr1, tr2 = st.columns([3, 1])
    tr1.line_chart(trend_df[["🔧 Tutor Limitation", "📖 Learning Difficulty", "💬 Intent Drift"]], height=220)
    tr2.bar_chart(trend_df[["Tổng hội thoại"]], height=220)
    st.caption(
        "Trái: % hội thoại/ngày rơi vào từng nhóm friction. Phải: tổng số hội thoại mỗi ngày — "
        "ngày mẫu nhỏ (cột thấp) thì % bên trái kém tin cậy."
    )
    st.divider()

    ctrl1, ctrl2 = st.columns([3, 1])
    selected_date = ctrl1.selectbox("Chọn ngày học", days, index=len(days) - 1 if days else 0, key="dash_date")
    ctrl2.write("")
    run_clicked = ctrl2.button(
        "▶ Phân tích bằng AI", type="primary", width="stretch", key="dash_run",
        help="Gọi AI đặt tên các chủ đề vướng mắc + viết gợi ý hành động. Kết quả được lưu lại, mỗi ngày chỉ cần chạy 1 lần.",
    )

    st.subheader(f"Ngày {selected_date}")

    day_report = build_day_cases(by_day[selected_date])
    total = day_report["total_conversations"]
    n_friction = day_report["n_friction_cases"]
    # Cụm đã được tính SẴN bằng Python (rule-based) — không tốn quota AI, luôn có ngay cả trước
    # khi bấm "Phân tích". AI chỉ ĐẶT TÊN + viết lý do cho các cụm này, không đổi số liệu.
    clusters = build_clusters(day_report["friction_cases"], transcript_idx, total)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng hội thoại", total)
    c2.metric("Có tín hiệu friction", n_friction)
    c3.metric("Tỷ lệ", f"{(n_friction / max(total, 1) * 100):.0f}%")
    c4.metric("Vấn đề riêng biệt", len(clusters), help="Số cụm friction đã gom theo (nhóm, từ khoá đại diện) — rule-based, chưa cần AI")

    st.markdown("**Phân bố 3 nhóm vướng mắc** *(đếm rule-based, số thật — không cần AI)*")
    b = day_report["category_breakdown"]
    cb1, cb2, cb3 = st.columns(3)
    cb1.metric("🔧 Tutor Limitation", f"{b['tutor_limitation']['percent']}%", help="AI Tutor chưa hỗ trợ được: không tìm thấy tài liệu / trả lời chưa đúng câu hỏi")
    cb2.metric("📖 Learning Difficulty", f"{b['learning_difficulty']['percent']}%", help="Học viên có dấu hiệu chưa hiểu: hỏi lại cùng khái niệm / cần giải thích nhiều lần")
    cb3.metric("💬 Learning Intent Drift", f"{b['intent_drift']['percent']}%", help="Không tập trung vào mục tiêu học: chào hỏi / câu hỏi ngoài phạm vi")
    dist_df = pd.DataFrame(
        {"% hội thoại trong ngày": [b["tutor_limitation"]["percent"], b["learning_difficulty"]["percent"], b["intent_drift"]["percent"]]},
        index=["🔧 Tutor Limitation", "📖 Learning Difficulty", "💬 Intent Drift"],
    )
    st.bar_chart(dist_df)

    if total < MIN_SAMPLE_SIZE:
        st.warning(
            f"⚠️ Ngày này chỉ có {total} hội thoại (< {MIN_SAMPLE_SIZE}) — mẫu quá nhỏ, "
            "kết quả % bên dưới có độ tin cậy thấp. Đây là hành vi mong muốn cho lớp chỗ khó "
            "② Mơ hồ/thiếu thông tin (spec.md §5-§6), không phải lỗi."
        )

    if n_friction == 0:
        st.info("Không có hội thoại nào có tín hiệu vướng mắc trong ngày này — không cần phân tích thêm.")
        return

    # ---- Đọc kết quả AI đã lưu (phiên hiện tại HOẶC file cache) TRƯỚC để dùng cho heatmap bên dưới ----
    _, result, _ = get_khoi2_state(selected_date)
    named_concepts = result.get("concepts", []) if result is not None else None

    st.markdown("**🗺️ Mức độ khó theo chủ đề** *(luôn có sẵn — tên khái niệm sẽ dễ đọc hơn sau khi bấm Phân tích bằng AI)*")
    if named_concepts:
        heat_rows = [{
            "Khái niệm": c["concept"], "Nhóm": CATEGORY_LABEL.get(c["category"], c["category"]),
            "Số hội thoại": c["case_count"], "% trong ngày": c["percent_of_day"],
            "Mức độ": severity_label(c["percent_of_day"]),
        } for c in named_concepts]
    else:
        heat_rows = [{
            "Khái niệm": f"{cl['cluster_id'].split('::', 1)[-1]} (chưa đặt tên bởi AI)",
            "Nhóm": CATEGORY_LABEL.get(cl["category"], cl["category"]),
            "Số hội thoại": cl["case_count"], "% trong ngày": cl["percent_of_day"],
            "Mức độ": severity_label(cl["percent_of_day"]),
        } for cl in clusters]
    st.dataframe(pd.DataFrame(heat_rows).sort_values("Số hội thoại", ascending=False), width="stretch", hide_index=True)

    st.markdown("**⚠️ Hội thoại đáng xem trước** *(ẩn danh — chỉ mã hội thoại, không hiện danh tính học viên)*")
    ranked = sorted(day_report["friction_cases"], key=lambda c: risk_score(c["signals"]), reverse=True)[:5]
    risk_rows = [{
        "Mã hội thoại": c["conversation_id"],
        "Nhóm chính": CATEGORY_LABEL.get(c["signals"]["primary_category"], c["signals"]["primary_category"]),
        "Điểm rủi ro": risk_score(c["signals"]),
        "Số lượt hỏi": c["signals"]["n_turns"],
        "Lặp trang nhiều nhất": c["signals"]["repeated_page_max"],
    } for c in ranked]
    st.dataframe(pd.DataFrame(risk_rows), width="stretch", hide_index=True)
    st.caption(
        "Công thức điểm rủi ro: số lượt hỏi + số lần lặp trang nhiều nhất + 2×(số lần AI phải cho "
        "đáp án trực tiếp) + 2×(số lần học viên tự nói 'không hiểu') + 2 nếu rating cuối là 'down'. "
        "100% rule-based — dùng để biết hội thoại nào đáng xem trước, không phải điểm rủi ro cá nhân "
        "học viên (spec.md §4 non-goal)."
    )

    st.divider()

    if run_clicked:
        with st.spinner("AI đang đặt tên các chủ đề vướng mắc..."):
            try:
                payload, result = classify_day(selected_date, day_report, transcript_idx, dry_run=False)
                st.session_state["payload"] = payload
                st.session_state["result"] = result
                st.session_state["date"] = selected_date
                if result is not None:
                    save_khoi2_result(selected_date, payload, result)
            except Exception as e:
                st.error(f"Lỗi khi gọi AI phân tích: {e}\n\nCần GROQ_API_KEY hợp lệ trong codebase/.env.")

    payload, result, from_cache = get_khoi2_state(selected_date)

    if payload is None or result is None:
        st.info("Bấm **▶ Phân tích bằng AI** ở trên để đặt tên các chủ đề vướng mắc và nhận gợi ý hành động.")
        return
    if from_cache:
        st.caption(
            f"💾 Kết quả đọc từ lần phân tích trước (`results/khoi2_{selected_date}.json`) "
            "— bấm **▶ Phân tích bằng AI** nếu muốn chạy lại."
        )

    concepts = result.get("concepts", [])
    st.success(f"Đã phân tích — {len(concepts)} khái niệm học viên đang vướng trong ngày {selected_date}.")
    if result.get("low_confidence_note"):
        st.warning(f"Ghi chú độ tin cậy: {result['low_confidence_note']}")

    st.markdown("**✅ Gợi ý hành động (tóm tắt)**")
    action_rows = [{
        "Mức độ": severity_label(c["percent_of_day"]), "Khái niệm": c["concept"],
        "% trong ngày": c["percent_of_day"], "Gợi ý hành động": c.get("suggested_action", ""),
    } for c in concepts]
    st.dataframe(
        pd.DataFrame(action_rows).sort_values("% trong ngày", ascending=False),
        width="stretch", hide_index=True,
    )

    st.markdown("**🔎 Conversation Explorer** *(chi tiết từng khái niệm — chọn để xem case gốc)*")
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


LOG_CATEGORY_FILTERS = {
    "🔧 Tutor Limitation": "tutor_limitation",
    "📖 Learning Difficulty": "learning_difficulty",
    "💬 Intent Drift": "intent_drift",
}


def render_log_tab(by_day):
    st.markdown(
        "<div style='padding:14px 18px;border-radius:14px;background:rgba(120,120,255,0.08);"
        "border:1px solid rgba(120,120,255,0.25);margin-bottom:12px;'>"
        "<b>🗂️ Nhật ký hội thoại</b> · <span style='opacity:0.7'>Đọc nguyên văn từng hội thoại học "
        "viên ↔ AI Tutor, kèm phân tích tín hiệu vướng mắc cho đúng hội thoại đang xem</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    DEMO_OPTION = "🧪 Phiên demo hiện tại (tab Chat)"
    days = sorted(by_day.keys())
    day_options = list(days)
    if st.session_state.get("demo_turns"):
        day_options.append(DEMO_OPTION)

    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 3])
    selected_date = ctrl1.selectbox(
        "Chọn ngày học", day_options,
        index=len(days) - 1 if days else 0, key="log_date",
    )
    category_filter = ctrl2.selectbox(
        "Lọc theo nhóm friction",
        ["Tất cả", *LOG_CATEGORY_FILTERS.keys(), "✅ Không friction"],
        key="log_cat_filter",
    )
    search = ctrl3.text_input(
        "Tìm theo mã hội thoại hoặc nội dung câu hỏi",
        placeholder="vd C0094 hoặc context window",
        key="log_search",
    )

    if selected_date == DEMO_OPTION:
        conversations = {"DEMO-CONV": st.session_state["demo_turns"]}
        st.info("Đang xem hội thoại demo live từ tab Chat — chạy qua ĐÚNG pipeline phân tích như log thật.")
    else:
        conversations = by_day.get(selected_date, {})
    turns_by_conv = dict(conversations)
    rows = []
    for conv_id, turns in conversations.items():
        sig = compute_conversation_signals(turns)
        rows.append({
            "conv_id": conv_id,
            "sig": sig,
            "Mã hội thoại": conv_id,
            "Nhóm chính": CATEGORY_LABEL.get(sig["primary_category"], "✅ Không friction"),
            "Điểm rủi ro": risk_score(sig),
            "Mức độ": conversation_risk_label(risk_score(sig)),
            "Số lượt hỏi": sig["n_turns"],
            "Lặp trang nhiều nhất": sig["repeated_page_max"],
            "Rating cuối": turns[-1]["rating"] or "—",
        })

    if category_filter in LOG_CATEGORY_FILTERS:
        wanted = LOG_CATEGORY_FILTERS[category_filter]
        rows = [r for r in rows if wanted in r["sig"]["categories"]]
    elif category_filter == "✅ Không friction":
        rows = [r for r in rows if not r["sig"]["friction_flag"]]

    if search:
        needle = search.strip().lower()
        rows = [
            r for r in rows
            if needle in r["conv_id"].lower()
            or any(needle in (t["question"] or "").lower() for t in turns_by_conv[r["conv_id"]])
        ]

    rows.sort(key=lambda r: r["Điểm rủi ro"], reverse=True)

    st.caption(f"{len(rows)} hội thoại khớp bộ lọc (trong tổng {len(conversations)} hội thoại ngày {selected_date}).")

    if not rows:
        st.info("Không có hội thoại nào khớp bộ lọc — thử đổi ngày hoặc bỏ bộ lọc.")
        return

    table_df = pd.DataFrame([{k: v for k, v in r.items() if k not in ("conv_id", "sig")} for r in rows])
    event = st.dataframe(
        table_df, hide_index=True, width="stretch", row_height=36,
        on_select="rerun", selection_mode="single-row-required", key="log_table",
    )

    selected_rows = event["selection"]["rows"] if isinstance(event, dict) else []
    chosen = rows[selected_rows[0]] if selected_rows else rows[0]
    conv_id, sig = chosen["conv_id"], chosen["sig"]
    conv_turns = turns_by_conv[conv_id]

    st.divider()
    col_chat, col_analysis = st.columns([2, 1])

    with col_chat:
        is_demo = selected_date == DEMO_OPTION
        user_label = conv_turns[0].get("user_id", "DEMO")
        topic_label = conv_turns[0].get("day_code", "phiên demo live" if is_demo else "—")
        date_label = "demo" if is_demo else selected_date

        head1, head2 = st.columns([3, 1])
        head1.markdown(f"**💬 Hội thoại `{conv_id}`** · Học viên `{user_label}` (ẩn danh)")
        head1.caption(f"Chủ đề: `{topic_label}`")
        export_lines = [f"Hội thoại {conv_id} — ngày {date_label} — chủ đề {topic_label}", ""]
        for t in conv_turns:
            prefix = f"[Trang {t['page']}] " if t["page"] else ""
            export_lines.append(f"HỌC VIÊN: {prefix}{t['question']}")
            export_lines.append(f"AI TUTOR ({t['move_used'] or '—'}): {t['tutor_content']}")
            export_lines.append("")
        head2.download_button(
            "⬇ Xuất hội thoại", "\n".join(export_lines),
            file_name=f"{conv_id}_{date_label}.txt", mime="text/plain",
            width="stretch", key="log_export",
        )
        for t in conv_turns:
            with st.chat_message("user"):
                if t["page"]:
                    page_caption = f"📄 Trang {t['page']}"
                    if t.get("selection"):
                        page_caption += f" · bôi đen: _{t['selection']}_"
                    st.caption(page_caption)
                st.write(t["question"] or "_(không có câu hỏi tự gõ)_")
            with st.chat_message("assistant"):
                st.write(t["tutor_content"])
                meta = f"move: `{t['move_used'] or '—'}`"
                if t["rating"]:
                    meta += " · rating: " + ("👍" if t["rating"] == "up" else "👎")
                st.caption(meta)

    with col_analysis:
        st.markdown("**🔍 Phân tích hội thoại** *(rule-based — kiểm lại được bằng tay)*")
        with st.container(border=True):
            friction_label = CATEGORY_LABEL.get(sig["primary_category"], "✅ Không có")
            st.markdown(f"**Loại friction:** {friction_label}")
            st.markdown(f"**Mức độ:** {conversation_risk_label(risk_score(sig))}")
            st.markdown(f"**Điểm rủi ro:** {risk_score(sig)}")
            other_cats = [c for c in sig["categories"] if c != sig["primary_category"]]
            if other_cats:
                st.caption("Nhóm khác cũng xuất hiện: " + ", ".join(CATEGORY_LABEL.get(c, c) for c in other_cats))
            st.divider()
            st.markdown("**Tín hiệu chi tiết**")
            st.caption(f"- Số lượt hỏi: {sig['n_turns']}")
            st.caption(
                f"- Lặp trang nhiều nhất: {sig['repeated_page_max']} lần"
                + (" ⚠️" if sig["repeated_page_flag"] else "")
            )
            st.caption(f"- Hỏi lại cùng khái niệm (đổi diễn đạt): {'Có' if sig['rephrase_flag'] else 'Không'}")
            st.caption(f"- Số lần AI cho đáp án trực tiếp: {sig['direct_answer_count']}")
            st.caption(f"- Học viên tự nói 'không hiểu': {sig.get('confusion_count', 0)} lần")
            st.caption(f"- Rating cuối là 'down': {'Có' if sig['rating_down_quit'] else 'Không'}")
            st.caption(f"- Số trang khác nhau đã hỏi: {len(sig['distinct_pages'])}")
        st.caption(
            "Công thức điểm rủi ro: số lượt hỏi + số lần lặp trang nhiều nhất + 2×(số lần AI phải "
            "cho đáp án trực tiếp) + 2×(số lần tự nói 'không hiểu') + 2 nếu rating cuối là 'down'. "
            "100% rule-based, không phải điểm AI đoán (giống bảng \"Hội thoại đáng xem trước\" ở tab Dashboard)."
        )


by_day, transcript_idx = load_all()

st.title("🎓 VLearn — AI Tutor & Class Insight")

tab_chat, tab_dashboard, tab_log = st.tabs([
    "🧑‍🎓 Chat với AI Tutor (học viên)",
    "📊 Dashboard Giảng viên/TA",
    "🗂️ Nhật ký hội thoại",
])

with tab_chat:
    render_chat_tab(transcript_idx)

with tab_dashboard:
    render_dashboard_tab(by_day, transcript_idx)

with tab_log:
    render_log_tab(by_day)
