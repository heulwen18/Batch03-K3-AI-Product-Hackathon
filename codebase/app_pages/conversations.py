"""Conversations — danh sách hội thoại theo tuần/ngày, đọc nguyên văn + panel phân tích."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui_common import (  # noqa: E402
    CATEGORY_LABEL, RISK_HELP, conversation_risk_label, load_all, risk_score, weeks_of,
)
from signals import compute_conversation_signals  # noqa: E402

DEMO_OPTION = "🧪 Phiên demo hiện tại (trang Chat)"
CATEGORY_FILTERS = {v: k for k, v in CATEGORY_LABEL.items()}

by_day, _ = load_all()
weeks = weeks_of(by_day.keys())

st.markdown("### 💬 Conversations")

f1, f2, f3, f4 = st.columns([2, 2, 2, 3])
week_label = f1.selectbox("Tuần", [w[0] for w in weeks], index=len(weeks) - 1, key="cv_week")
week_days = dict(weeks)[week_label]
day_options = ["Cả tuần"] + week_days
if st.session_state.get("demo_turns"):
    day_options.append(DEMO_OPTION)
day_choice = f2.selectbox("Ngày", day_options, key="cv_day")
category_filter = f3.selectbox("Nhóm", ["Tất cả", *CATEGORY_FILTERS.keys(), "✅ Không có vấn đề"], key="cv_cat")
search = f4.text_input("Tìm kiếm", placeholder="mã hội thoại hoặc nội dung câu hỏi...", key="cv_search")

# ---- Gom hội thoại theo phạm vi ----
if day_choice == DEMO_OPTION:
    conversations = {("demo", "DEMO-CONV"): st.session_state["demo_turns"]}
    st.info("Đang xem hội thoại demo live từ trang Chat — chạy qua đúng pipeline phân tích như log thật.")
elif day_choice == "Cả tuần":
    conversations = {(d, cid): ts for d in week_days for cid, ts in by_day[d].items()}
else:
    conversations = {(day_choice, cid): ts for cid, ts in by_day[day_choice].items()}

rows = []
for (d, cid), turns in conversations.items():
    sig = compute_conversation_signals(turns)
    rows.append({
        "_key": (d, cid), "_sig": sig,
        "Mã hội thoại": cid, "Ngày": d,
        "Nhóm chính": CATEGORY_LABEL.get(sig["primary_category"], "✅ Normal"),
        "Điểm rủi ro": risk_score(sig),
        "Mức độ": conversation_risk_label(risk_score(sig)),
        "Số lượt hỏi": sig["n_turns"],
        "Rating cuối": turns[-1]["rating"] or "—",
    })

if category_filter in CATEGORY_FILTERS:
    wanted = CATEGORY_FILTERS[category_filter]
    rows = [r for r in rows if wanted in r["_sig"]["categories"]]
elif category_filter == "✅ Không có vấn đề":
    rows = [r for r in rows if not r["_sig"]["friction_flag"]]
if search:
    needle = search.strip().lower()
    rows = [r for r in rows if needle in r["Mã hội thoại"].lower()
            or any(needle in (t["question"] or "").lower() for t in conversations[r["_key"]])]

rows.sort(key=lambda r: r["Điểm rủi ro"], reverse=True)
st.caption(f"{len(rows)} hội thoại khớp bộ lọc (trong tổng {len(conversations)} hội thoại của phạm vi đang chọn).")

if not rows:
    st.info("Không có hội thoại nào khớp bộ lọc — thử đổi tuần/ngày hoặc bỏ bộ lọc.")
    st.stop()

table_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
event = st.dataframe(
    table_df, hide_index=True, width="stretch", row_height=36, height=280,
    on_select="rerun", selection_mode="single-row-required", key="cv_table",
    column_config={"Điểm rủi ro": st.column_config.NumberColumn(help=RISK_HELP)},
)
selected_rows = event["selection"]["rows"] if isinstance(event, dict) else []
chosen = rows[selected_rows[0]] if selected_rows else rows[0]
(day_key, conv_id), sig = chosen["_key"], chosen["_sig"]
conv_turns = conversations[chosen["_key"]]

st.divider()
col_chat, col_analysis = st.columns([2, 1])

with col_chat:
    is_demo = day_key == "demo"
    user_label = conv_turns[0].get("user_id", "DEMO")
    topic_label = conv_turns[0].get("day_code", "phiên demo live" if is_demo else "—")

    head1, head2 = st.columns([3, 1])
    head1.markdown(f"**Conversation `{conv_id}`** · Học viên `{user_label}` (ẩn danh) · {day_key}")
    head1.caption(f"Chủ đề buổi học: `{topic_label}`")
    export_lines = [f"Hội thoại {conv_id} — {day_key} — chủ đề {topic_label}", ""]
    for t in conv_turns:
        prefix = f"[Trang {t['page']}] " if t["page"] else ""
        export_lines.append(f"HỌC VIÊN: {prefix}{t['question']}")
        export_lines.append(f"AI TUTOR ({t['move_used'] or '—'}): {t['tutor_content']}")
        export_lines.append("")
    head2.download_button(
        "⬇ Xuất hội thoại", "\n".join(export_lines),
        file_name=f"{conv_id}_{day_key}.txt", mime="text/plain", width="stretch", key="cv_export",
    )
    for t in conv_turns:
        with st.chat_message("user"):
            if t["page"]:
                cap = f"📄 Trang {t['page']}"
                if t.get("selection"):
                    cap += f" · bôi đen: _{t['selection']}_"
                st.caption(cap)
            st.write(t["question"] or "_(không có câu hỏi tự gõ)_")
        with st.chat_message("assistant"):
            st.write(t["tutor_content"])
            meta = f"move: `{t['move_used'] or '—'}`"
            if t["rating"]:
                meta += " · rating: " + ("👍" if t["rating"] == "up" else "👎")
            st.caption(meta)

with col_analysis:
    st.markdown("**Phân tích hội thoại**", help="Toàn bộ tín hiệu đếm từ nội dung hội thoại — kiểm lại được bằng tay, không phải điểm AI đoán.")
    with st.container(border=True):
        friction_label = CATEGORY_LABEL.get(sig["primary_category"], "✅ Không có")
        st.markdown(f"**Loại vấn đề:** {friction_label}")
        st.markdown(f"**Mức độ:** {conversation_risk_label(risk_score(sig))}")
        st.markdown(f"**Điểm rủi ro:** {risk_score(sig)}", help=RISK_HELP)
        other = [c for c in sig["categories"] if c != sig["primary_category"]]
        if other:
            st.caption("Nhóm khác cũng xuất hiện: " + ", ".join(CATEGORY_LABEL.get(c, c) for c in other))
        st.divider()
        st.markdown("**Tín hiệu chi tiết**")
        st.caption(f"- Số lượt hỏi: {sig['n_turns']}")
        st.caption(f"- Lặp trang nhiều nhất: {sig['repeated_page_max']} lần" + (" ⚠️" if sig["repeated_page_flag"] else ""))
        st.caption(f"- Hỏi lại cùng khái niệm: {'Có' if sig['rephrase_flag'] else 'Không'}")
        st.caption(f"- AI cho đáp án trực tiếp: {sig['direct_answer_count']} lần")
        st.caption(f"- Tự nói 'không hiểu': {sig.get('confusion_count', 0)} lần")
        st.caption(f"- Rating cuối là 'down': {'Có' if sig['rating_down_quit'] else 'Không'}")
        st.caption(f"- Số trang khác nhau đã hỏi: {len(sig['distinct_pages'])}")
