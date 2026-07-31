"""Reports — tổng hợp theo tuần: KPI có so sánh tuần trước, xu hướng, heatmap chủ đề × ngày."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui_common import (  # noqa: E402
    CATEGORY_HELP, CATEGORY_LABEL, MIN_SAMPLE_SIZE, NORMAL_LABEL,
    build_week_report, load_all, per_day_frame, severity_label, weeks_of,
)
from classify_friction import build_clusters  # noqa: E402
from transcript_index import keywords as extract_keywords  # noqa: E402

by_day, transcript_idx = load_all()
weeks = weeks_of(by_day.keys())

h1, h2 = st.columns([3, 1])
h1.markdown("### 📑 Reports")
week_label = h2.selectbox("Tuần", [w[0] for w in weeks], index=len(weeks) - 1, key="rp_week")
week_idx = [w[0] for w in weeks].index(week_label)
week_days = weeks[week_idx][1]

report = build_week_report(by_day, tuple(week_days))
prev = build_week_report(by_day, tuple(weeks[week_idx - 1][1])) if week_idx > 0 else None

total = report["total_conversations"]
b = report["category_breakdown"]
normal_pct = (total - report["n_friction_cases"]) / max(total, 1) * 100


def delta(cur, prv):
    return None if prv is None else f"{cur - prv:+.1f}%"


k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Tổng cuộc hội thoại", total,
          delta=None if prev is None else total - prev["total_conversations"],
          help=f"{len(week_days)} ngày có dữ liệu trong tuần; so sánh với tuần liền trước")
k2.metric("📖 Learning Difficulty", f"{b['learning_difficulty']['percent']}%",
          delta=delta(b["learning_difficulty"]["percent"], prev and prev["category_breakdown"]["learning_difficulty"]["percent"]),
          delta_color="inverse", help=CATEGORY_HELP["learning_difficulty"])
k2.caption(f"{b['learning_difficulty']['count']} hội thoại")
k3.metric("🔧 Tutor Limitation", f"{b['tutor_limitation']['percent']}%",
          delta=delta(b["tutor_limitation"]["percent"], prev and prev["category_breakdown"]["tutor_limitation"]["percent"]),
          delta_color="inverse", help=CATEGORY_HELP["tutor_limitation"])
k3.caption(f"{b['tutor_limitation']['count']} hội thoại")
k4.metric("💬 Off-topic / Drift", f"{b['intent_drift']['percent']}%",
          delta=delta(b["intent_drift"]["percent"], prev and prev["category_breakdown"]["intent_drift"]["percent"]),
          delta_color="inverse", help=CATEGORY_HELP["intent_drift"])
k4.caption(f"{b['intent_drift']['count']} hội thoại")
prev_normal = None if prev is None else (prev["total_conversations"] - prev["n_friction_cases"]) / max(prev["total_conversations"], 1) * 100
k5.metric("✅ Normal / No issue", f"{normal_pct:.0f}%", delta=delta(normal_pct, prev_normal))
k5.caption(f"{total - report['n_friction_cases']} hội thoại")

if total < MIN_SAMPLE_SIZE:
    st.warning(f"⚠️ Tuần này chỉ có {total} hội thoại (< {MIN_SAMPLE_SIZE}) — mẫu quá nhỏ, % có độ tin cậy thấp.")

# ---- Xu hướng theo thời gian + top vấn đề + phân tích xu hướng ----
c1, c2, c3 = st.columns([5, 3, 3])
with c1:
    with st.container(border=True):
        st.markdown("**Xu hướng theo thời gian**", help="Số hội thoại từng nhóm theo ngày (cột chồng); mỗi cột kèm tổng ngày đó")
        st.bar_chart(per_day_frame(report), height=280)

clusters = build_clusters(report["friction_cases"], transcript_idx, total)
with c2:
    with st.container(border=True):
        st.markdown(f"**Top vấn đề ({len(week_days)} ngày)**")
        for i, cl in enumerate(clusters[:6], 1):
            kw = cl["cluster_id"].split("::", 1)[-1]
            st.markdown(f"{i}. **{kw}** — {cl['case_count']} lượt ({cl['percent_of_day']:.1f}%)")
        if not clusters:
            st.caption("Không có vấn đề nào.")

with c3:
    with st.container(border=True):
        st.markdown("**Phân tích xu hướng**", help="So sánh % từng nhóm với tuần liền trước — tính từ số đếm, không phải AI nhận định")
        if prev is None:
            st.caption("Chưa có tuần trước để so sánh.")
        else:
            for cat in ("learning_difficulty", "tutor_limitation", "intent_drift"):
                cur, prv = b[cat]["percent"], prev["category_breakdown"][cat]["percent"]
                arrow = "↓ giảm" if cur < prv else ("↑ tăng" if cur > prv else "→ giữ nguyên")
                st.markdown(f"**{CATEGORY_LABEL[cat]}** {arrow} {abs(cur - prv):.1f}% so với tuần trước ({prv}% → {cur}%)")

# ---- Heatmap chủ đề × ngày + phân bố ----
c4, c5 = st.columns([3, 2])
with c4:
    with st.container(border=True):
        st.markdown("**Heatmap chủ đề × ngày**", help="Số hội thoại của từng chủ đề (từ khoá đại diện) theo ngày trong tuần")
        top_kws = [cl["cluster_id"].split("::", 1)[-1] for cl in clusters[:6]]
        heat = {kw: {d: 0 for d in week_days} for kw in top_kws}
        for case in report["friction_cases"]:
            combined = " ".join(t["question"] for t in case["turns"])
            kws = extract_keywords(combined)
            case_day = next((d for d in week_days if case in report["per_day"][d]["friction_cases"]), None)
            if case_day:
                for kw in top_kws:
                    if kw in kws:
                        heat[kw][case_day] += 1
        heat_df = pd.DataFrame(
            [{"Chủ đề": kw, **{d[5:]: heat[kw][d] for d in week_days},
              "Tổng": sum(heat[kw].values())} for kw in top_kws]
        )
        if not heat_df.empty:
            st.dataframe(heat_df.sort_values("Tổng", ascending=False), width="stretch", hide_index=True)
        else:
            st.caption("Không có dữ liệu.")

with c5:
    with st.container(border=True):
        st.markdown("**Phân bố mức độ theo chủ đề**")
        dist_rows = [{
            "Chủ đề": cl["cluster_id"].split("::", 1)[-1],
            "Mức độ": severity_label(cl["percent_of_day"]),
            "Số hội thoại": cl["case_count"],
        } for cl in clusters[:8]]
        if dist_rows:
            st.dataframe(pd.DataFrame(dist_rows), width="stretch", hide_index=True)
        else:
            st.caption("Không có dữ liệu.")

# ---- Xuất báo cáo ----
lines = [f"BÁO CÁO TUẦN — {week_label}", f"Tổng hội thoại: {total}", ""]
for cat in ("learning_difficulty", "tutor_limitation", "intent_drift"):
    lines.append(f"{CATEGORY_LABEL[cat]}: {b[cat]['count']} hội thoại ({b[cat]['percent']}%)")
lines.append(f"{NORMAL_LABEL}: {total - report['n_friction_cases']} hội thoại ({normal_pct:.0f}%)")
lines.append("")
lines.append("TOP VẤN ĐỀ:")
for i, cl in enumerate(clusters[:10], 1):
    lines.append(f"{i}. {cl['cluster_id'].split('::', 1)[-1]} — {cl['case_count']} lượt ({cl['percent_of_day']:.1f}%) — {cl['root_cause']}")
st.download_button("⬇ Xuất báo cáo", "\n".join(lines), file_name=f"bao-cao-{week_label.split('·')[0].strip()}.txt",
                   mime="text/plain", key="rp_export")
