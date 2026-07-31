import ast
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from shared_taskbar import get_active_page, render_taskbar, taskbar_css

DEFAULT_CSV_PATH = "../data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv"

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

CONVERSATION_LIST_HEIGHT = 632
# The middle tab panes scroll internally and align visually with the left/right columns.
CHAT_THREAD_HEIGHT = 712
CHAT_INFO_HEIGHT = 712


def inject_styles() -> None:
    # ----------------------------------------------------------------------------
    # STYLES
    # ----------------------------------------------------------------------------
    st.markdown(
        """
        <style>
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
            --mock-sidebar-width: 154px;
            --content-max-width: 1288px;
            --font-ui: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
            --font-size-ui: 12.5px;
        }
    
        * { box-sizing: border-box; }
        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMarkdownContainer"],
        [data-baseweb],
        button, input, textarea, select, svg text {
            font-family: var(--font-ui) !important;
        }
        .stApp { background: var(--canvas); color: var(--ink); }
        #MainMenu, footer,
        [data-testid="stHeader"], [data-testid="stToolbar"],
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
            display: none !important;
        }
        [data-testid="stAppViewContainer"] > .main {
            background: var(--canvas);
            padding-left: 0 !important;
        }
    
        [data-testid="stVerticalBlock"] { gap: 0; }
    
        .block-container {
            width: min(var(--content-max-width), calc(100vw - var(--mock-sidebar-width)));
            max-width: min(var(--content-max-width), calc(100vw - var(--mock-sidebar-width)));
            min-width: 0;
            margin-left: var(--mock-sidebar-width) !important;
            margin-right: 0;
            padding-bottom: 2rem;
            padding-left: 16px;
            padding-right: 16px;
            padding-top: 15px;
        }
    
    
        .page-title {
            color: var(--ink);
            display: inline-block;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-right: 10px;
        }
        .header-meta {
            color: var(--muted);
            font-size: var(--font-size-ui);
            margin-left: 10px;
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
            margin-bottom: 11px;
            padding: 12px 13px;
            transition: border-color 150ms ease, background-color 150ms ease;
        }
        .conv-item:hover { border-color: #CFC8FA; }
        .conv-item-selected {
            background: var(--purple-soft);
            border-color: var(--purple);
        }
        .conv-item-title { color: var(--ink); font-size: 13px; font-weight: 750; }
        .conv-item-time { color: var(--muted); font-size: 11px; }
        .conv-item-snippet {
            color: var(--ink-soft);
            font-size: var(--font-size-ui);
            line-height: 1.45;
            margin-top: 4px;
        }
    
        .bubble-row { display: flex; margin-bottom: 14px; }
        .avatar {
            align-items: center;
            border-radius: 50%;
            display: flex;
            flex-shrink: 0;
            font-size: 12px;
            height: 22px;
            justify-content: center;
            margin-right: 8px;
            width: 22px;
        }
        .avatar-student { background: var(--purple-soft); }
        .avatar-tutor { background: var(--success-soft); }
        .msg-name { color: var(--ink); font-size: 13px; font-weight: 750; }
        .msg-time { color: var(--muted); font-size: 11px; margin-left: 7px; }
        .msg-content {
            color: var(--ink-soft);
            font-size: var(--font-size-ui);
            line-height: 1.55;
            margin-top: 3px;
            white-space: pre-wrap;
        }
    
        .field-row {
            border-bottom: 1px solid #EFF0F4;
            display: flex;
            font-size: var(--font-size-ui);
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
            font-weight: 400;
            margin: 3px 4px 3px 0;
            padding: 4px 8px;
        }
    
        .analysis-copy {
            color: var(--ink-soft);
            font-size: var(--font-size-ui);
            font-weight: 500;
            line-height: 1.62;
            overflow: visible;
            white-space: normal;
            overflow-wrap: break-word;
            word-break: break-word;
        }
        .analysis-copy + .analysis-copy { margin-top: 4px; }
        .st-key-analysis_card .field-row,
        .st-key-analysis_card .badge,
        .st-key-summary_card .analysis-copy,
        .st-key-recommendation_card .analysis-copy,
        .st-key-knowledge_card .analysis-copy,
        .st-key-tags_card .tag-pill {
            font-size: var(--font-size-ui);
        }
        .st-key-summary_card .card-title,
        .st-key-recommendation_card .card-title,
        .st-key-knowledge_card .card-title,
        .st-key-tags_card .card-title {
            line-height: 1.35;
            margin-bottom: 12px;
        }
        .st-key-summary_card .analysis-copy,
        .st-key-recommendation_card .analysis-copy,
        .st-key-knowledge_card .analysis-copy {
            color: var(--ink-soft);
            display: block;
            font-size: var(--font-size-ui);
            font-weight: 500;
            line-height: 1.62;
            overflow: visible;
            padding: 1px 0 8px;
        }
        .st-key-recommendation_card .analysis-copy {
            padding: 2px 0 9px;
        }
        .st-key-tags_card .tag-pill {
            line-height: 1.35;
            padding-bottom: 5px;
            padding-top: 5px;
        }
        .st-key-analysis_card [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-summary_card [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-recommendation_card [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-knowledge_card [data-testid="stVerticalBlockBorderWrapper"],
        .st-key-tags_card [data-testid="stVerticalBlockBorderWrapper"] {
            height: auto !important;
            max-height: none !important;
            overflow: visible !important;
        }
        .st-key-analysis_card [data-testid="stMarkdownContainer"],
        .st-key-summary_card [data-testid="stMarkdownContainer"],
        .st-key-recommendation_card [data-testid="stMarkdownContainer"],
        .st-key-knowledge_card [data-testid="stMarkdownContainer"],
        .st-key-tags_card [data-testid="stMarkdownContainer"] {
            overflow: visible;
            white-space: normal;
        }
        .st-key-analysis_card .field-row {
            align-items: flex-start;
            gap: 10px;
            line-height: 1.55;
            overflow: visible;
        }
        .st-key-analysis_card .field-label,
        .st-key-analysis_card .field-value,
        .st-key-analysis_card .badge,
        .st-key-tags_card .tag-pill {
            max-width: 100%;
            white-space: normal;
            overflow-wrap: break-word;
            word-break: break-word;
        }
    
        .st-key-chat_column_shell {
            margin-top: -7px;
        }
        .st-key-chat_column_shell [data-baseweb="tab-list"] {
            margin-top: 0;
        }
    
        .st-key-chat_thread_scroll [data-testid="stVerticalBlock"],
        .st-key-chat_info_scroll [data-testid="stVerticalBlock"],
        .st-key-conversation_list_scroll [data-testid="stVerticalBlock"] {
            padding-right: 4px;
        }
        .st-key-conversation_mode_filter {
            margin-top: 7px;
            margin-bottom: 10px;
        }
        .st-key-conversation_list_scroll [data-testid="stButton"] {
            margin-top: 6px;
            margin-bottom: 20px;
        }
        .st-key-conversation_list_scroll [data-testid="stButton"] button {
            background: #FFFFFF !important;
            border-color: #E3E6EF !important;
            border-radius: 7px;
            color: var(--purple-dark) !important;
            font-family: var(--font-ui) !important;
            font-size: var(--font-size-ui) !important;
            font-weight: 650 !important;
            line-height: 1.2 !important;
            min-height: 29px;
        }
        .st-key-conversation_list_scroll [data-testid="stButton"] *,
        .st-key-conversation_list_scroll button * {
            color: var(--purple-dark) !important;
            font-family: var(--font-ui) !important;
            font-size: var(--font-size-ui) !important;
            font-weight: 650 !important;
            line-height: 1.2 !important;
        }
        .st-key-chat_thread_scroll ::-webkit-scrollbar,
        .st-key-chat_info_scroll ::-webkit-scrollbar,
        .st-key-conversation_list_scroll ::-webkit-scrollbar {
            width: 6px;
        }
        .st-key-chat_thread_scroll ::-webkit-scrollbar-thumb,
        .st-key-chat_info_scroll ::-webkit-scrollbar-thumb,
        .st-key-conversation_list_scroll ::-webkit-scrollbar-thumb {
            background: #D8DDEA;
            border-radius: 999px;
        }
    
        .nav-item {
            border-radius: 6px;
            color: #34394C;
            font-size: var(--font-size-ui);
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
            background: #FFFFFF !important;
            border-color: var(--border) !important;
            border-radius: 6px;
            color: #5C38D0 !important;
            font-family: var(--font-ui) !important;
            font-size: var(--font-size-ui) !important;
            font-weight: 700 !important;
            min-height: 29px;
        }
        [data-testid="stButton"] button *,
        [data-testid="stDownloadButton"] button * {
            color: inherit !important;
            font-family: inherit !important;
            font-size: inherit !important;
            font-weight: inherit !important;
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {
            background: #F8F6FF !important;
            border-color: var(--purple) !important;
            color: var(--purple-dark) !important;
        }
        [data-testid="stButton"] button[kind="primary"],
        [data-testid="stDownloadButton"] button[kind="primary"] {
            background: var(--purple) !important;
            border-color: var(--purple) !important;
            color: #FFFFFF !important;
        }
        [data-testid="stButton"] button:disabled,
        [data-testid="stDownloadButton"] button:disabled,
        [data-testid="stDownloadButton"] [aria-disabled="true"] {
            background: #F4F5F8 !important;
            border-color: #E4E7EF !important;
            color: #A0A5B6 !important;
            opacity: 1 !important;
        }
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div {
            background: var(--surface) !important;
            border-color: var(--border) !important;
            border-radius: 6px;
        }
        .st-key-conversation_mode_filter [data-baseweb="select"] > div,
        .st-key-conversation_mode_filter [role="combobox"] {
            background: #FFFFFF !important;
            color: var(--ink-soft) !important;
        }
        .st-key-conversation_mode_filter [data-baseweb="select"] > div,
        .st-key-conversation_mode_filter [role="combobox"] {
            height: 30px !important;
            min-height: 30px !important;
        }
        [data-baseweb="input"] input,
        [data-baseweb="select"] {
            color: var(--ink-soft);
            font-family: var(--font-ui);
            font-size: var(--font-size-ui);
        }
        .st-key-conversation_mode_filter input,
        .st-key-conversation_mode_filter [role="combobox"],
        .st-key-conversation_mode_filter [data-baseweb="select"],
        .st-key-conversation_mode_filter [data-baseweb="select"] *,
        [role="listbox"],
        [role="listbox"] *,
        [role="option"],
        [data-baseweb="menu"],
        [data-baseweb="menu"] *,
        [data-baseweb="popover"] [role="option"],
        [data-baseweb="popover"] [role="option"] * {
            font-family: var(--font-ui) !important;
            font-size: var(--font-size-ui) !important;
            font-weight: 400 !important;
            line-height: 1.35 !important;
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
            font-family: var(--font-ui);
            font-size: var(--font-size-ui);
            font-weight: 700;
            height: 30px;
            min-height: 30px;
            padding-bottom: 0;
            padding-top: 0;
        }
        [aria-selected="true"][data-baseweb="tab"] { color: var(--purple-dark); }
        [data-baseweb="tab-highlight"] { background-color: var(--purple); }
        .conv-item-snippet,
        .msg-content,
        .field-row,
        .analysis-copy,
        .st-key-summary_card .analysis-copy,
        .st-key-recommendation_card .analysis-copy,
        .st-key-knowledge_card .analysis-copy,
        [role="tab"],
        [role="tab"] *,
        [data-baseweb="tab"],
        [data-baseweb="tab"] *,
        [data-testid="stDownloadButton"],
        [data-testid="stDownloadButton"] *,
        [data-testid="stButton"] button,
        [role="button"],
        [role="button"] * {
            font-family: var(--font-ui) !important;
            font-size: var(--font-size-ui) !important;
        }
    
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
        .st-key-analysis_card,
        .st-key-summary_card,
        .st-key-recommendation_card,
        .st-key-knowledge_card,
        .st-key-tags_card {
            margin-bottom: 14px;
            padding: 14.07px 18px !important;
        }
        .st-key-analysis_card {
            margin-top: -7px;
        }
        .st-key-tags_card { margin-bottom: 0; padding-bottom: 14.53px !important; }
        .st-key-analysis_card > [data-testid="stElementContainer"]:first-child,
        .st-key-summary_card > [data-testid="stElementContainer"]:first-child,
        .st-key-recommendation_card > [data-testid="stElementContainer"]:first-child,
        .st-key-knowledge_card > [data-testid="stElementContainer"]:first-child,
        .st-key-tags_card > [data-testid="stElementContainer"]:first-child {
            margin-bottom: 8px;
        }
        .st-key-analysis_card > [data-testid="stElementContainer"]:not(:first-child) {
            margin-bottom: 2px;
        }
        .st-key-analysis_card > [data-testid="stElementContainer"]:last-child {
            margin-bottom: 0;
        }
        .st-key-summary_card .analysis-copy,
        .st-key-knowledge_card .analysis-copy {
            line-height: 1.7;
        }
        .st-key-recommendation_card > [data-testid="stElementContainer"] {
            margin-bottom: 3px;
        }
        .st-key-recommendation_card > [data-testid="stElementContainer"]:first-child {
            margin-bottom: 8px;
        }
        .st-key-recommendation_card .st-key-rec_btn {
            margin-top: 10px;
        }
        .st-key-tags_card .tag-pill {
            margin: 5px 5px 4px 0;
        }
    
        @media (min-width: 1350px) {
            :root {
                --mock-sidebar-width: 165px;
                --content-max-width: 1328px;
            }
            .mock-sidebar { padding: 12px 11px 11px; }
            .block-container { padding-left: 18px; padding-right: 18px; padding-top: 22px; }
            .page-title { font-size: 26px; }
        }
        @media (max-width: 1100px) {
            :root {
                --mock-sidebar-width: 140px;
                --content-max-width: calc(100vw - var(--mock-sidebar-width));
            }
            .mock-sidebar { padding: 12px 9px 10px; }
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .page-title { font-size: 20px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<style>" + taskbar_css("fixed") + "</style>", unsafe_allow_html=True)

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


def render(pipeline_mode: str = "Static demo") -> None:
    # ----------------------------------------------------------------------------
    # FIXED LEFT TASKBAR - shared component
    # ----------------------------------------------------------------------------
    inject_styles()
    uploaded = None
    render_taskbar("conversations", pipeline_mode)
    
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
                f'<span class="header-meta">'
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
    
    st.markdown("<div style='height:34px;'></div>", unsafe_allow_html=True)
    
    # ----------------------------------------------------------------------------
    # THREE COLUMN LAYOUT
    # ----------------------------------------------------------------------------
    col_list, col_chat, col_analysis = st.columns([1.0, 1.5, 1.0], gap="small")
    
    # --- COLUMN 1: conversation list -----------------------------------------
    with col_list:
        st.markdown('<div class="card-title">Danh sách hội thoại</div>', unsafe_allow_html=True)
        mode_options = ["Tất cả mức độ"] + sorted(FRICTION_LABELS.keys())
        mode_filter = st.selectbox(
            "Lọc",
            mode_options,
            format_func=lambda x: x if x == "Tất cả mức độ" else FRICTION_LABELS[x][0],
            label_visibility="collapsed",
            key="conversation_mode_filter",
        )
    
        filtered = summaries.copy()
        if mode_filter != "Tất cả mức độ":
            filtered = filtered[filtered["friction_type"] == mode_filter]
    
        with st.container(height=CONVERSATION_LIST_HEIGHT, border=False, key="conversation_list_scroll"):
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
                                <span class="badge" style="color:{fg};background:{bg};">{label}</span>
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
        with st.container(key="chat_column_shell"):
            tab_chat, tab_info = st.tabs(["Hội thoại", "Thông tin chung"])
    
            conv_msgs = df[df["conversation_id"] == st.session_state.selected_conv].sort_values("_row_order")
    
            with tab_chat:
                with st.container(height=CHAT_THREAD_HEIGHT, border=False, key="chat_thread_scroll"):
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
    
            with tab_info:
                with st.container(height=CHAT_INFO_HEIGHT, border=False, key="chat_info_scroll"):
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
            # Placeholder severity (not present in source CSV yet)
            severity_key = "high" if sel_row["friction_type"] in ("learning_difficulty", "tutor_limitation") else "low"
            severity_label, severity_fg, severity_bg = SEVERITY_LABELS[severity_key]
    
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
                        f"<div class='analysis-copy'>"
                        f"Học viên có dấu hiệu: <b>{miscon_text}</b>. {STATIC_INSIGHT}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='analysis-copy'>{STATIC_INSIGHT}</div>",
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
                        f"<div class='analysis-copy'>• {rec}</div>",
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
                    f"<div class='analysis-copy'>{STATIC_INSIGHT}</div>",
                    unsafe_allow_html=True,
                )
    
            # Tag liên quan (static)
            with st.container(border=True, key="tags_card", gap="xsmall"):
                st.markdown('<div class="card-title">🏷️ Tag liên quan</div>', unsafe_allow_html=True)
                tags_html = "".join(f'<span class="tag-pill">{t}</span>' for t in STATIC_TAGS)
                st.markdown(tags_html + '<span class="tag-pill">+</span>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="AI Learning Analytics Copilot",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    page = get_active_page(default="conversations")
    if page == "dashboard":
        import dashboard as dashboard_page

        dashboard_page.render()
    else:
        render()


if __name__ == "__main__":
    main()
