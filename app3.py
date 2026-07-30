import ast
import io
from datetime import datetime

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Learning Analytics Copilot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULT_CSV_PATH = "data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv"

# Static placeholder data used whenever the source CSV does not contain the
# corresponding information yet. Replace these with real fields/tables once
# they exist in the pipeline (classification model output, RAG tags, etc.)
FRICTION_LABELS = {
    "learning_difficulty": ("Learning Difficulty", "#7C5CFC", "#F0ECFF"),
    "tutor_limitation": ("Tutor Limitation", "#C76A25", "#FFE8D9"),
    "off_topic": ("Off-topic", "#375A9F", "#DBE7FF"),
    "normal": ("Normal", "#2D7354", "#DDF5E9"),
}

SEVERITY_LABELS = {
    "high": ("Cao", "#C93654", "#FFE8ED"),
    "medium": ("Trung bình", "#C76A25", "#FFE8D9"),
    "low": ("Thấp", "#2D7354", "#DDF5E9"),
}

STATIC_INSIGHT = (
    "Nhiều học viên gặp khó khăn với khái niệm \"Context Window\". "
    "Cần nhấn mạnh ví dụ thực tế và phân biệt rõ với \"Memory\"."
)

STATIC_RECOMMENDATIONS = [
    "Thêm ví dụ trực quan so sánh Context vs Memory",
    "Sử dụng diagram để minh họa sự khác biệt",
    "Đề xuất slide bổ sung về \"Context Window\" trong buổi học sắp tới",
]

STATIC_TAGS = ["context", "memory", "window size", "token", "RAG", "attention", "long-term memory"]

NAV_ITEMS = [
    ("📊", "Live Dashboard"),
    ("💬", "Conversations"),
    ("📄", "Reports"),
    ("⚙️", "Settings"),
]

# ----------------------------------------------------------------------------
# STYLES
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --ink: #111528;
        --ink-soft: #4C5265;
        --muted: #8F96AA;
        --border: #E8EBF3;
        --purple: #7557F6;
        --purple-dark: #6747EA;
        --purple-soft: #F0ECFF;
        --canvas: #F6F7FB;
        --surface: #FFFFFF;
        --success: #23C980;
        --success-text: #2D7354;
        --success-soft: #DDF5E9;
    }

    * { box-sizing: border-box; }
    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
            "Segoe UI", sans-serif;
    }
    .stApp { background: var(--canvas); color: var(--ink); }
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stAppViewContainer"] > .main { background: var(--canvas); }
    [data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }

    .block-container {
        max-width: 1500px;
        padding-bottom: 2rem;
        padding-top: 1.25rem;
    }

    .breadcrumb {
        color: var(--muted);
        font-size: 12px;
        font-weight: 500;
        margin-bottom: 5px;
    }
    .page-title {
        color: var(--ink);
        display: inline-block;
        font-size: 24px;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-right: 10px;
    }

    .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(18, 26, 48, 0.015);
        margin-bottom: 12px;
        padding: 16px 18px;
    }
    .card-title {
        color: #2E3344;
        font-size: 13px;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .badge {
        border-radius: 5px;
        display: inline-block;
        font-size: 11px;
        font-weight: 700;
        line-height: 1.3;
        padding: 3px 8px;
    }

    .conv-item {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        cursor: pointer;
        margin-bottom: 7px;
        padding: 10px 11px;
        transition: border-color 150ms ease, background-color 150ms ease;
    }
    .conv-item:hover { border-color: #CFC8FA; }
    .conv-item-selected {
        background: var(--purple-soft);
        border-color: var(--purple);
    }
    .conv-item-title { color: var(--ink); font-size: 12px; font-weight: 750; }
    .conv-item-time { color: var(--muted); font-size: 10.5px; }
    .conv-item-snippet {
        color: var(--ink-soft);
        font-size: 12px;
        line-height: 1.4;
        margin-top: 4px;
    }

    .bubble-row { display: flex; margin-bottom: 18px; }
    .avatar {
        align-items: center;
        border-radius: 50%;
        display: flex;
        flex-shrink: 0;
        font-size: 14px;
        height: 32px;
        justify-content: center;
        margin-right: 10px;
        width: 32px;
    }
    .avatar-student { background: var(--purple-soft); }
    .avatar-tutor { background: var(--success-soft); }
    .msg-name { color: var(--ink); font-size: 12.5px; font-weight: 750; }
    .msg-time { color: var(--muted); font-size: 10.5px; margin-left: 8px; }
    .msg-content {
        color: var(--ink-soft);
        font-size: 13px;
        line-height: 1.55;
        margin-top: 3px;
        white-space: pre-wrap;
    }

    .field-row {
        border-bottom: 1px solid #EFF0F4;
        display: flex;
        font-size: 12px;
        justify-content: space-between;
        padding: 7px 0;
    }
    .field-row:last-child { border-bottom: 0; }
    .field-label { color: var(--muted); }
    .field-value { color: var(--ink); font-weight: 650; }

    .progress-track {
        background: #EEEAFD;
        border-radius: 5px;
        height: 5px;
        margin-top: 7px;
        overflow: hidden;
        width: 100%;
    }
    .progress-fill { background: var(--purple); border-radius: inherit; height: 5px; }

    .tag-pill {
        background: #F4F5F8;
        border-radius: 5px;
        color: #777D8F;
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        margin: 3px 4px 3px 0;
        padding: 4px 8px;
    }

    .nav-item {
        border-radius: 6px;
        color: #34394C;
        font-size: 13px;
        font-weight: 650;
        margin-bottom: 3px;
        padding: 8px 10px;
    }
    .nav-item-active {
        background: var(--purple-soft);
        color: var(--purple-dark);
        font-weight: 750;
    }

    .side-live {
        background: #FAFBFD;
        border: 1px solid #E8EAF0;
        border-radius: 8px;
        color: #747A8D;
        font-size: 11px;
        line-height: 1.5;
        padding: 10px 11px;
    }
    .side-live b { color: #25A36B; font-weight: 700; }

    [data-testid="stButton"] button,
    [data-testid="stDownloadButton"] button {
        border-color: var(--border);
        border-radius: 6px;
        color: var(--ink-soft);
        font-family: inherit;
        font-size: 12px;
        font-weight: 700;
        min-height: 2.25rem;
    }
    [data-testid="stButton"] button:hover,
    [data-testid="stDownloadButton"] button:hover {
        border-color: var(--purple);
        color: var(--purple-dark);
    }
    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stDownloadButton"] button[kind="primary"] {
        background: var(--purple);
        border-color: var(--purple);
        color: #FFFFFF;
    }
    [data-baseweb="input"] > div,
    [data-baseweb="select"] > div {
        background: var(--surface);
        border-color: var(--border);
        border-radius: 6px;
    }
    [data-baseweb="input"] input,
    [data-baseweb="select"] {
        color: var(--ink-soft);
        font-family: inherit;
        font-size: 12px;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: #FAFBFD;
        border-color: var(--border);
        border-radius: 8px;
    }
    [data-baseweb="tab-list"] {
        border-bottom: 1px solid var(--border);
        gap: 18px;
    }
    [data-baseweb="tab"] {
        color: var(--muted);
        font-family: inherit;
        font-size: 12px;
        font-weight: 700;
    }
    [aria-selected="true"][data-baseweb="tab"] { color: var(--purple-dark); }
    [data-baseweb="tab-highlight"] { background-color: var(--purple); }

    .st-key-technical_info_card [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-analysis_card [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-summary_card [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-knowledge_card [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-tags_card [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border-color: var(--border);
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(18, 26, 48, 0.015);
    }
    .st-key-recommendation_card [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFF8EF;
        border-color: #FFE3C6;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(18, 26, 48, 0.015);
    }

    @media (max-width: 1100px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .page-title { font-size: 21px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------
LIST_COLS = ["citations", "misconceptions", "follow_ups"]


def _parse_list_cell(x):
    if pd.isna(x) or x == "":
        return []
    if isinstance(x, list):
        return x
    try:
        val = ast.literal_eval(x)
        if isinstance(val, list):
            return val
        return [val]
    except Exception:
        return [str(x)]


@st.cache_data
def load_data(file_bytes: bytes | None, default_path: str) -> pd.DataFrame:
    if file_bytes is not None:
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_csv(default_path)

    for col in LIST_COLS:
        if col in df.columns:
            df[col] = df[col].apply(_parse_list_cell)
        else:
            df[col] = [[] for _ in range(len(df))]

    if "message_created_at" in df.columns:
        df["message_created_at"] = pd.to_datetime(df["message_created_at"], errors="coerce")

    # Preserve original row order as the conversation turn order (CSV has no
    # explicit sequence column across roles within a turn).
    df["_row_order"] = range(len(df))
    return df


def classify_friction(tutor_texts: list[str]) -> str:
    """Very small heuristic placeholder for the friction-type classifier.
    Swap this out once a real classification field/model exists."""
    joined = " ".join(tutor_texts).lower()
    if "không tìm thấy" in joined or "xin lỗi" in joined:
        return "tutor_limitation"
    if "nhầm lẫn" in joined or "chưa hiểu" in joined or "mơ hồ" in joined:
        return "learning_difficulty"
    if not tutor_texts:
        return "off_topic"
    return "normal"


def build_conversation_summaries(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for conv_id, g in df.groupby("conversation_id", sort=False):
        g = g.sort_values("_row_order")
        student_msgs = g[g["role"] == "student"]["content"].tolist()
        tutor_msgs = g[g["role"] == "tutor"]["content"].tolist()
        friction = classify_friction(tutor_msgs)
        last_msg = g.iloc[-1]
        first_msg = g.iloc[0]
        snippet = (student_msgs[0] if student_msgs else (tutor_msgs[0] if tutor_msgs else "")).replace("\n", " ")
        misconceptions = sorted({m for lst in g["misconceptions"] for m in lst})
        records.append(
            {
                "conversation_id": conv_id,
                "day_code": first_msg.get("day_code", ""),
                "conversation_mode": first_msg.get("conversation_mode", ""),
                "friction_type": friction,
                "start_time": g["message_created_at"].min(),
                "end_time": g["message_created_at"].max(),
                "n_messages": len(g),
                "snippet": snippet[:70] + ("…" if len(snippet) > 70 else ""),
                "misconceptions": misconceptions,
                "llm_call_count": g["llm_call_count"].max() if "llm_call_count" in g else None,
                "models_used": g["models_used"].mode().iloc[0] if "models_used" in g and not g["models_used"].mode().empty else "",
                "total_input_tokens": g["total_input_tokens"].sum() if "total_input_tokens" in g else 0,
                "total_output_tokens": g["total_output_tokens"].sum() if "total_output_tokens" in g else 0,
                "total_cost_usd": g["total_cost_usd"].sum() if "total_cost_usd" in g else 0,
                "avg_latency_ms": g["avg_latency_ms"].mean() if "avg_latency_ms" in g else 0,
            }
        )
    summary = pd.DataFrame(records).sort_values("start_time", ascending=False).reset_index(drop=True)
    return summary


# ----------------------------------------------------------------------------
# SIDEBAR (left global nav) - mostly static, mirrors the mock-up
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎓 AI Learning\nAnalytics Copilot")
    st.markdown("<br>", unsafe_allow_html=True)
    for icon, label in NAV_ITEMS:
        active = "nav-item-active" if label == "Conversations" else ""
        st.markdown(f'<div class="nav-item {active}">{icon} &nbsp; {label}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="side-live">🟢 Live Processing<br>'
        'Đang xử lý dữ liệu thời gian thực<br><b>~ 512 hội thoại/phút</b></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("Nguồn dữ liệu")
    uploaded = st.file_uploader("Tải file CSV hội thoại", type="csv", label_visibility="collapsed")

# ----------------------------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------------------------
file_bytes = uploaded.getvalue() if uploaded is not None else None
try:
    df = load_data(file_bytes, DEFAULT_CSV_PATH)
except Exception as e:
    st.error(f"Không đọc được file CSV: {e}")
    st.stop()

summaries = build_conversation_summaries(df)

if "selected_conv" not in st.session_state:
    st.session_state.selected_conv = summaries.iloc[0]["conversation_id"] if len(summaries) else None

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown(
        '<div class="breadcrumb">🏠 Conversations &nbsp;›&nbsp; Context Window vs Memory &nbsp;›&nbsp; '
        f'{st.session_state.selected_conv}</div>',
        unsafe_allow_html=True,
    )
    sel_row = summaries[summaries["conversation_id"] == st.session_state.selected_conv]
    sel_row = sel_row.iloc[0] if len(sel_row) else None
    friction_label, friction_fg, friction_bg = FRICTION_LABELS.get(
        sel_row["friction_type"] if sel_row is not None else "normal", FRICTION_LABELS["normal"]
    )
    header_line = f'<span class="page-title">Conversation #{st.session_state.selected_conv}</span> '
    header_line += (
        f'<span class="badge" style="color:{friction_fg};background:{friction_bg};">{friction_label}</span>'
    )
    if sel_row is not None and pd.notna(sel_row["start_time"]):
        header_line += (
            f'<span style="color:#8F96AA;font-size:12px;margin-left:10px;">'
            f'{sel_row["start_time"].strftime("%H:%M %p · %d/%m/%Y")}</span>'
        )
    st.markdown(header_line, unsafe_allow_html=True)

with top_r:
    if sel_row is not None:
        conv_msgs = df[df["conversation_id"] == st.session_state.selected_conv].sort_values("_row_order")
        transcript = "\n\n".join(
            f'[{r.role}] {r.message_created_at}\n{r.content}' for r in conv_msgs.itertuples()
        )
        st.download_button(
            "⬇ Xuất hội thoại",
            data=transcript.encode("utf-8"),
            file_name=f"{st.session_state.selected_conv}.txt",
            mime="text/plain",
            width="stretch",
        )

st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# THREE COLUMN LAYOUT
# ----------------------------------------------------------------------------
col_list, col_chat, col_analysis = st.columns([1.15, 1.75, 1.15], gap="medium")

# --- COLUMN 1: conversation list -----------------------------------------
with col_list:
    st.markdown('<div class="card-title">Danh sách hội thoại</div>', unsafe_allow_html=True)
    mode_options = ["Tất cả mức độ"] + sorted(FRICTION_LABELS.keys())
    mode_filter = st.selectbox(
        "Lọc",
        mode_options,
        format_func=lambda x: x if x == "Tất cả mức độ" else FRICTION_LABELS[x][0],
        label_visibility="collapsed",
    )
    search = st.text_input("Tìm kiếm…", label_visibility="collapsed", placeholder="🔎 Tìm kiếm…")

    filtered = summaries.copy()
    if mode_filter != "Tất cả mức độ":
        filtered = filtered[filtered["friction_type"] == mode_filter]
    if search:
        filtered = filtered[
            filtered["snippet"].str.contains(search, case=False, na=False)
            | filtered["conversation_id"].str.contains(search, case=False, na=False)
        ]

    for _, row in filtered.iterrows():
        label, fg, bg = FRICTION_LABELS.get(row["friction_type"], FRICTION_LABELS["normal"])
        selected = row["conversation_id"] == st.session_state.selected_conv
        time_str = row["start_time"].strftime("%H:%M") if pd.notna(row["start_time"]) else ""
        btn_key = f"btn_{row['conversation_id']}"
        with st.container():
            st.markdown(
                f"""
                <div class="conv-item {'conv-item-selected' if selected else ''}">
                    <div style="display:flex;justify-content:space-between;">
                        <span class="conv-item-title">#{row['conversation_id']}</span>
                        <span class="badge" style="color:{fg};background:{bg};font-size:10.5px;">{label}</span>
                    </div>
                    <div class="conv-item-time">{time_str}</div>
                    <div class="conv-item-snippet">{row['snippet']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Xem", key=btn_key, width="stretch"):
                st.session_state.selected_conv = row["conversation_id"]
                st.rerun()

# --- COLUMN 2: chat thread -------------------------------------------------
with col_chat:
    tab_chat, tab_info = st.tabs(["Hội thoại", "Thông tin chung"])

    conv_msgs = df[df["conversation_id"] == st.session_state.selected_conv].sort_values("_row_order")

    with tab_chat:
        for r in conv_msgs.itertuples():
            is_student = r.role == "student"
            avatar_cls = "avatar-student" if is_student else "avatar-tutor"
            avatar_icon = "🧑‍🎓" if is_student else "🤖"
            name = f"Học viên {getattr(r, 'user_id', '')}" if is_student else "AI Tutor"
            time_str = r.message_created_at.strftime("%H:%M:%S") if pd.notna(r.message_created_at) else ""
            content_html = str(r.content).replace("\n", "<br>")
            st.markdown(
                f"""
                <div class="bubble-row">
                    <div class="avatar {avatar_cls}">{avatar_icon}</div>
                    <div>
                        <span class="msg-name">{name}</span><span class="msg-time">{time_str}</span>
                        <div class="msg-content">{content_html}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.text_input("Nhập ghi chú…", label_visibility="collapsed", key="note_input")
        st.button("⬇ Lưu ghi chú", width="content")

    with tab_info:
        if sel_row is not None:
            with st.container(border=True, key="technical_info_card", gap=None):
                st.markdown(
                    '<div class="card-title">Thông tin kỹ thuật (từ dữ liệu CSV)</div>',
                    unsafe_allow_html=True,
                )
                info_fields = [
                    ("Ngày/Buổi học", sel_row["day_code"]),
                    ("Chế độ hội thoại", sel_row["conversation_mode"]),
                    ("Số lượt gọi LLM", int(sel_row["llm_call_count"]) if pd.notna(sel_row["llm_call_count"]) else "-"),
                    ("Model sử dụng", sel_row["models_used"]),
                    ("Tổng input tokens", int(sel_row["total_input_tokens"])),
                    ("Tổng output tokens", int(sel_row["total_output_tokens"])),
                    ("Tổng chi phí (USD)", f"{sel_row['total_cost_usd']:.4f}"),
                    ("Độ trễ trung bình (ms)", int(sel_row["avg_latency_ms"])),
                ]
                for label, value in info_fields:
                    st.markdown(
                        f'<div class="field-row"><span class="field-label">{label}</span>'
                        f'<span class="field-value">{value}</span></div>',
                        unsafe_allow_html=True,
                    )

# --- COLUMN 3: AI analysis --------------------------------------------------
with col_analysis:
    if sel_row is not None:
        friction_label, friction_fg, friction_bg = FRICTION_LABELS.get(
            sel_row["friction_type"], FRICTION_LABELS["normal"]
        )
        # Placeholder severity + confidence (not present in source CSV yet)
        severity_key = "high" if sel_row["friction_type"] in ("learning_difficulty", "tutor_limitation") else "low"
        severity_label, severity_fg, severity_bg = SEVERITY_LABELS[severity_key]
        confidence_pct = 87  # static placeholder

        with st.container(border=True, key="analysis_card", gap=None):
            st.markdown('<div class="card-title">Phân tích của AI</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="field-row"><span class="field-label">Loại friction</span>'
                f'<span class="badge" style="color:{friction_fg};background:{friction_bg};">{friction_label}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="field-row"><span class="field-label">Mức độ</span>'
                f'<span class="badge" style="color:{severity_fg};background:{severity_bg};">{severity_label}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="field-row" style="flex-direction:column;align-items:flex-start;">'
                f'<div style="display:flex;justify-content:space-between;width:100%;">'
                f'<span class="field-label">Độ tin cậy</span><span class="field-value">{confidence_pct}%</span></div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{confidence_pct}%;"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="field-row"><span class="field-label">Chủ đề</span>'
                f'<span class="badge" style="color:#6747EA;background:#F0ECFF;">{sel_row["day_code"]}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="field-row"><span class="field-label">Thời gian bắt đầu</span>'
                f'<span class="field-value">{sel_row["start_time"].strftime("%H:%M:%S") if pd.notna(sel_row["start_time"]) else "-"}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="field-row"><span class="field-label">Thời gian kết thúc</span>'
                f'<span class="field-value">{sel_row["end_time"].strftime("%H:%M:%S") if pd.notna(sel_row["end_time"]) else "-"}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="field-row"><span class="field-label">Số lượt trao đổi</span>'
                f'<span class="field-value">{sel_row["n_messages"]} tin nhắn</span></div>',
                unsafe_allow_html=True,
            )

        # Tóm tắt vấn đề (static placeholder narrative, seeded with real misconceptions if any)
        with st.container(border=True, key="summary_card", gap="xsmall"):
            st.markdown('<div class="card-title">📝 Tóm tắt vấn đề</div>', unsafe_allow_html=True)
            if sel_row["misconceptions"]:
                miscon_text = "; ".join(sel_row["misconceptions"])
                st.markdown(
                    f"<div style='font-size:13px;color:#4C5265;line-height:1.6;'>"
                    f"Học viên có dấu hiệu: <b>{miscon_text}</b>. {STATIC_INSIGHT}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='font-size:13px;color:#4C5265;line-height:1.6;'>{STATIC_INSIGHT}</div>",
                    unsafe_allow_html=True,
                )

        # Khuyến nghị hành động (static)
        with st.container(border=True, key="recommendation_card", gap="xsmall"):
            st.markdown(
                '<div class="card-title" style="color:#C76A25;">💡 Khuyến nghị hành động</div>',
                unsafe_allow_html=True,
            )
            for rec in STATIC_RECOMMENDATIONS:
                st.markdown(
                    f"<div style='font-size:13px;color:#4C5265;'>• {rec}</div>",
                    unsafe_allow_html=True,
                )
            st.button("Xem gợi ý chi tiết →", key="rec_btn")

        # Trích xuất kiến thức (static)
        with st.container(border=True, key="knowledge_card", gap="xsmall"):
            st.markdown(
                '<div class="card-title" style="color:#6747EA;">📚 Trích xuất kiến thức</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='font-size:13px;color:#4C5265;line-height:1.6;'>{STATIC_INSIGHT}</div>",
                unsafe_allow_html=True,
            )

        # Tag liên quan (static)
        with st.container(border=True, key="tags_card", gap="xsmall"):
            st.markdown('<div class="card-title">🏷️ Tag liên quan</div>', unsafe_allow_html=True)
            tags_html = "".join(f'<span class="tag-pill">{t}</span>' for t in STATIC_TAGS)
            st.markdown(tags_html + '<span class="tag-pill">+</span>', unsafe_allow_html=True)
