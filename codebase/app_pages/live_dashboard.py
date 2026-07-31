"""Live Dashboard — tổng quan tuần/ngày: KPI, friction theo ngày, top vấn đề, hội thoại cần chú ý."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui_common import (  # noqa: E402
    CATEGORY_HELP, CATEGORY_LABEL, MIN_SAMPLE_SIZE, NORMAL_LABEL, RISK_HELP,
    build_week_report, get_ai_state, load_all, per_day_frame, risk_score,
    set_ai_state, severity_label, weeks_of,
)
from signals import build_day_cases  # noqa: E402
from classify_friction import build_clusters, classify_day  # noqa: E402

by_day, transcript_idx = load_all()
weeks = weeks_of(by_day.keys())

# ---- Bộ chọn phạm vi: tuần + ngày trong tuần ----
head_l, head_r = st.columns([3, 2])
head_l.markdown("### 📡 Live Dashboard")
with head_r:
    f1, f2 = st.columns(2)
    week_label = f1.selectbox("Tuần", [w[0] for w in weeks], index=len(weeks) - 1, key="ld_week")
    week_days = dict(weeks)[week_label]
    day_choice = f2.selectbox("Ngày", ["Cả tuần"] + week_days, key="ld_day")

if day_choice == "Cả tuần":
    scope_key, scope_days = f"tuan{week_label.split('·')[0].strip().split()[-1]}", week_days
    report = build_week_report(by_day, tuple(week_days))
else:
    scope_key, scope_days = day_choice, [day_choice]
    report = build_day_cases(by_day[day_choice])

total = report["total_conversations"]
n_friction = report["n_friction_cases"]
b = report["category_breakdown"]
clusters = build_clusters(report["friction_cases"], transcript_idx, total)

# ---- KPI cards (5 thẻ như mockup) ----
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Tổng cuộc hội thoại", total, help=f"Số hội thoại trong phạm vi đang chọn ({len(scope_days)} ngày)")
k2.metric("📖 Learning Difficulty", f"{b['learning_difficulty']['percent']}%", help=CATEGORY_HELP["learning_difficulty"])
k2.caption(f"{b['learning_difficulty']['count']} hội thoại")
k3.metric("🔧 Tutor Limitation", f"{b['tutor_limitation']['percent']}%", help=CATEGORY_HELP["tutor_limitation"])
k3.caption(f"{b['tutor_limitation']['count']} hội thoại")
k4.metric("💬 Off-topic / Drift", f"{b['intent_drift']['percent']}%", help=CATEGORY_HELP["intent_drift"])
k4.caption(f"{b['intent_drift']['count']} hội thoại")
normal = total - n_friction
k5.metric("✅ Normal / No issue", f"{(normal / max(total, 1) * 100):.0f}%")
k5.caption(f"{normal} hội thoại")

if total < MIN_SAMPLE_SIZE:
    st.warning(
        f"⚠️ Phạm vi này chỉ có {total} hội thoại (< {MIN_SAMPLE_SIZE}) — mẫu quá nhỏ, "
        "các tỷ lệ % có độ tin cậy thấp."
    )

# ---- Hàng giữa: friction theo ngày | top vấn đề | hội thoại cần chú ý ----
c_chart, c_top, c_alert = st.columns([5, 3, 3])

with c_chart:
    with st.container(border=True):
        st.markdown("**Learning friction theo ngày**")
        if day_choice == "Cả tuần":
            df = per_day_frame(report)[[
                CATEGORY_LABEL["learning_difficulty"], CATEGORY_LABEL["tutor_limitation"], CATEGORY_LABEL["intent_drift"],
            ]]
            st.line_chart(df, height=260)
        else:
            st.bar_chart(pd.DataFrame(
                {"Số hội thoại": [b[c]["count"] for c in ("learning_difficulty", "tutor_limitation", "intent_drift")]},
                index=[CATEGORY_LABEL["learning_difficulty"], CATEGORY_LABEL["tutor_limitation"], CATEGORY_LABEL["intent_drift"]],
            ), height=260)

with c_top:
    with st.container(border=True):
        st.markdown("**Top vấn đề**", help="Cụm hội thoại cùng chủ đề, xếp theo số hội thoại bị ảnh hưởng")
        for i, cl in enumerate(clusters[:5], 1):
            kw = cl["cluster_id"].split("::", 1)[-1]
            st.markdown(f"{i}. **{kw}** — {cl['case_count']} lượt · {severity_label(cl['percent_of_day'])}")
        if not clusters:
            st.caption("Không có vấn đề nào trong phạm vi này.")

with c_alert:
    with st.container(border=True):
        st.markdown("**Hội thoại cần chú ý**", help=RISK_HELP)
        ranked = sorted(report["friction_cases"], key=lambda c: risk_score(c["signals"]), reverse=True)[:4]
        for case in ranked:
            sig = case["signals"]
            label = CATEGORY_LABEL.get(sig["primary_category"], "")
            st.markdown(f"**`{case['conversation_id']}`** · {label}")
            st.caption(f"Điểm rủi ro {risk_score(sig)} · {sig['n_turns']} lượt hỏi → xem chi tiết ở trang Conversations")
        if not ranked:
            st.caption("Không có hội thoại nào cần chú ý.")

# ---- Khuyến nghị hành động (từ kết quả AI đã lưu) ----
_, ai_result, from_cache = get_ai_state(scope_key)
rec_col, btn_col = st.columns([4, 1])
with rec_col:
    if ai_result and ai_result.get("concepts"):
        top = max(ai_result["concepts"], key=lambda c: c["case_count"])
        st.info(f"**Khuyến nghị hành động:** {top.get('suggested_action', '')} — *{top['concept']}* "
                f"({top['case_count']} hội thoại{' · từ lần phân tích trước' if from_cache else ''})")
    else:
        st.info("**Khuyến nghị hành động:** bấm **Phân tích bằng AI** để đặt tên vấn đề và nhận gợi ý.")
with btn_col:
    if st.button("✨ Phân tích bằng AI", type="primary", width="stretch", key="ld_run",
                 help="AI đặt tên các vấn đề + viết gợi ý hành động. Kết quả được lưu, mỗi phạm vi chỉ cần chạy 1 lần."):
        with st.spinner("AI đang phân tích..."):
            try:
                payload, result = classify_day(scope_key, report, transcript_idx, dry_run=False)
                set_ai_state(scope_key, payload, result)
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi gọi AI: {e} — cần GROQ_API_KEY hợp lệ trong codebase/.env.")

# ---- Bản đồ chủ đề + bảng chi tiết ----
map_col, table_col = st.columns([2, 3])
with map_col:
    with st.container(border=True):
        st.markdown("**Bản đồ chủ đề**")
        tiles = ai_result["concepts"][:6] if ai_result else clusters[:6]
        grid = st.columns(2)
        for i, t in enumerate(tiles):
            name = t.get("concept") or t["cluster_id"].split("::", 1)[-1]
            with grid[i % 2].container(border=True):
                st.markdown(f"**{t['case_count']}**  ·  {t['percent_of_day']:.0f}%")
                st.caption(name)
        if not tiles:
            st.caption("Chưa có dữ liệu.")

with table_col:
    with st.container(border=True):
        st.markdown("**Mức độ khó theo chủ đề**",
                    help="Tên chủ đề sẽ dễ đọc hơn sau khi bấm Phân tích bằng AI; số hội thoại luôn đi kèm mọi dòng.")
        if ai_result:
            rows = [{
                "Chủ đề": c["concept"], "Nhóm": CATEGORY_LABEL.get(c["category"], c["category"]),
                "Số hội thoại": c["case_count"], "%": c["percent_of_day"],
                "Mức độ": severity_label(c["percent_of_day"]),
                "Gợi ý hành động": c.get("suggested_action", ""),
            } for c in ai_result.get("concepts", [])]
        else:
            rows = [{
                "Chủ đề": cl["cluster_id"].split("::", 1)[-1],
                "Nhóm": CATEGORY_LABEL.get(cl["category"], cl["category"]),
                "Số hội thoại": cl["case_count"], "%": cl["percent_of_day"],
                "Mức độ": severity_label(cl["percent_of_day"]), "Gợi ý hành động": "",
            } for cl in clusters]
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values("Số hội thoại", ascending=False),
                         width="stretch", hide_index=True, height=290)
        else:
            st.caption("Không có vấn đề nào trong phạm vi này.")
