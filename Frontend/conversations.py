import ast
import hashlib
import html
import io
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from shared_taskbar import get_active_page

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
DEFAULT_CSV_PATH = "../data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_TRANSCRIPT_CHARS = 12000

GEMINI_INSIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "problem_summary": {"type": "string"},
        "action_recommendations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "knowledge_extraction": {"type": "string"},
        "related_tags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "problem_summary",
        "action_recommendations",
        "knowledge_extraction",
        "related_tags",
    ],
}
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
            --mock-sidebar-width: 144px;
            --content-max-width: 1288px;
        }
    
                * { box-sizing: border-box; }
        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMarkdownContainer"],
        [data-baseweb],
        button, input, textarea, select {
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif !important;
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
            font-size: 13px;
            line-height: 1.45;
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
        .msg-name { color: var(--ink); font-size: 13px; font-weight: 750; }
        .msg-time { color: var(--muted); font-size: 11px; margin-left: 8px; }
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
            font-size: 13px;
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
            font-size: 13px;
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
        .st-key-summary_card .card-title,
        .st-key-recommendation_card .card-title,
        .st-key-knowledge_card .card-title,
        .st-key-tags_card .card-title,
        .st-key-summary_card .analysis-copy,
        .st-key-recommendation_card .analysis-copy,
        .st-key-knowledge_card .analysis-copy,
        .st-key-tags_card .tag-pill {
            font-size: 13px;
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
            font-size: 13px;
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
        .st-key-conversation_search {
            margin-bottom: 14px;
        }
        .st-key-conversation_list_scroll [data-testid="stButton"] {
            margin-top: 6px;
            margin-bottom: 20px;
        }
        .st-key-conversation_list_scroll [data-testid="stButton"] button {
            background: #FFFFFF;
            border-color: #E3E6EF;
            border-radius: 7px;
            color: var(--purple-dark);
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            line-height: 20.8px !important;
            min-height: 35px;
        }
        .st-key-conversation_list_scroll [data-testid="stButton"] *,
        .st-key-conversation_list_scroll button * {
            color: var(--purple-dark) !important;
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            line-height: 20.8px !important;
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
            font-size: 13px;
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
            font-size: 13px;
        }
        .st-key-conversation_mode_filter input,
        .st-key-conversation_mode_filter [role="combobox"],
        .st-key-conversation_mode_filter [data-baseweb="select"],
        .st-key-conversation_mode_filter [data-baseweb="select"] *,
        .st-key-conversation_search input,
        .st-key-conversation_search input::placeholder,
        [role="listbox"],
        [role="listbox"] *,
        [role="option"],
        [data-baseweb="menu"],
        [data-baseweb="menu"] *,
        [data-baseweb="popover"] [role="option"],
        [data-baseweb="popover"] [role="option"] * {
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            line-height: 20.8px !important;
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
            font-size: 13px;
            font-weight: 700;
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
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif !important;
            font-size: 13px !important;
        }
        .conv-item-snippet,
        .msg-content,
        .analysis-copy,
        .st-key-summary_card .analysis-copy,
        .st-key-recommendation_card .analysis-copy,
        .st-key-knowledge_card .analysis-copy,
        [role="tab"],
        [role="tab"] *,
        [data-testid="stDownloadButton"],
        [data-testid="stDownloadButton"] *,
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button,
        [data-testid="stDownloadButton"] a,
        button,
        [role="button"],
        [role="button"] * {
            font-weight: 400 !important;
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
                --mock-sidebar-width: 154px;
                --content-max-width: 1328px;
            }
            .mock-sidebar { padding: 12px 11px 11px; }
            .block-container { padding-left: 18px; padding-right: 18px; padding-top: 22px; }
        }
        @media (max-width: 1100px) {
            :root {
                --mock-sidebar-width: 122px;
                --content-max-width: calc(100vw - var(--mock-sidebar-width));
            }
            .mock-sidebar { padding: 12px 9px 10px; }
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

def read_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for env_path in (PROJECT_DIR / ".env", APP_DIR / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key.startswith("export "):
                key = key[7:].strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                values[key] = value
    return values


def get_config_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    env_values = read_env_values()
    for name in names:
        value = env_values.get(name, "").strip()
        if value:
            return value
    try:
        for name in names:
            value = str(st.secrets.get(name, "")).strip()
            if value:
                return value
    except Exception:
        pass
    return default


def get_gemini_api_key() -> str:
    return get_config_value("GEMINI_API_KEY", "GOOGLE_API_KEY")


def get_gemini_model() -> str:
    return get_config_value("GEMINI_MODEL", default=DEFAULT_GEMINI_MODEL)


def gemini_key_fingerprint(api_key: str) -> str:
    if not api_key:
        return "no-key"
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def compact_transcript(text: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    head_len = max_chars // 2
    tail_len = max_chars - head_len
    return text[:head_len] + "\n\n[... transcript truncated ...]\n\n" + text[-tail_len:]


def build_transcript_for_model(messages: pd.DataFrame) -> str:
    rows = []
    for row in messages.itertuples():
        role = "Student" if getattr(row, "role", "") == "student" else "AI Tutor"
        created_at = getattr(row, "message_created_at", None)
        time_str = created_at.strftime("%H:%M:%S") if pd.notna(created_at) else ""
        content = str(getattr(row, "content", "")).strip()
        if content:
            rows.append(f"{role} {time_str}:\n{content}")
    return compact_transcript("\n\n".join(rows))


def normalize_string_list(value, fallback: list[str], limit: int) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = fallback
    cleaned = []
    for item in items:
        text = str(item).strip()
        if text and text not in cleaned:
            cleaned.append(text[:180])
        if len(cleaned) >= limit:
            break
    return cleaned or fallback[:limit]


def static_conversation_insights(misconceptions: list[str] | None = None) -> dict:
    misconception_text = "; ".join(str(item).strip() for item in (misconceptions or []) if str(item).strip())
    if misconception_text:
        problem_summary = f"Học viên có dấu hiệu: {misconception_text}. {STATIC_INSIGHT}"
    else:
        problem_summary = STATIC_INSIGHT
    return {
        "problem_summary": problem_summary,
        "action_recommendations": STATIC_RECOMMENDATIONS,
        "knowledge_extraction": STATIC_INSIGHT,
        "related_tags": STATIC_TAGS,
        "source": "static",
    }


def strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def extract_text_from_gemini_response(data) -> str:
    """Return the final visible model text, skipping Gemini thought parts.

    Gemini 3.x may return more than one part. The old implementation returned
    the first text part, which can be a thought/debug part instead of the final
    JSON payload.
    """
    if not isinstance(data, dict):
        return ""

    candidates = data.get("candidates")
    if isinstance(candidates, list):
        visible_parts: list[str] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            parts = candidate.get("content", {}).get("parts", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                if not isinstance(part, dict) or part.get("thought") is True:
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    visible_parts.append(text.strip())
        if visible_parts:
            return "\n".join(visible_parts)

    for key in ("output_text", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def parse_gemini_json(text: str) -> dict:
    """Parse a Gemini JSON response even when it is wrapped in prose/fences."""
    cleaned = strip_json_fence(text)
    attempts = [cleaned]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        attempts.append(cleaned[start : end + 1])

    last_error: Exception | None = None
    for candidate in attempts:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                return parsed[0]
        except json.JSONDecodeError as exc:
            last_error = exc
    raise ValueError(f"Gemini không trả về JSON object hợp lệ: {last_error}")


def normalize_conversation_insights(raw: dict, fallback: dict) -> dict:
    if not isinstance(raw, dict):
        return fallback
    problem_summary = str(raw.get("problem_summary") or fallback["problem_summary"]).strip()
    knowledge_extraction = str(raw.get("knowledge_extraction") or fallback["knowledge_extraction"]).strip()
    return {
        "problem_summary": problem_summary[:700] or fallback["problem_summary"],
        "action_recommendations": normalize_string_list(
            raw.get("action_recommendations"), fallback["action_recommendations"], 5
        ),
        "knowledge_extraction": knowledge_extraction[:700] or fallback["knowledge_extraction"],
        "related_tags": normalize_string_list(raw.get("related_tags"), fallback["related_tags"], 8),
        "source": "gemini",
    }


def build_gemini_prompt(
    conversation_id: str,
    transcript: str,
    friction_label: str,
    severity_label: str,
    topic: str,
) -> str:
    return f"""
Analyze one AI tutoring conversation for an instructor dashboard.
Return only JSON that matches the provided schema. All values must be concise Vietnamese.
Do not invent facts outside the transcript. If evidence is weak, say it carefully.

Conversation ID: {conversation_id}
Detected friction: {friction_label}
Severity: {severity_label}
Topic/source: {topic}

Transcript:
{transcript}
""".strip()


def get_conversation_insights(
    conversation_id: str,
    transcript: str,
    friction_label: str,
    severity_label: str,
    topic: str,
    misconceptions: list[str],
    api_key_fingerprint: str,
    model: str,
) -> dict:
    # Keep the fingerprint in the signature so a changed API key produces a new
    # Streamlit session cache key. Never expose the real key to the UI.
    del api_key_fingerprint

    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "problem_summary": "Chưa thể phân tích vì ứng dụng chưa đọc được GEMINI_API_KEY.",
            "action_recommendations": ["Kiểm tra file .env hoặc st.secrets rồi tải lại trang."],
            "knowledge_extraction": "Chưa có dữ liệu do Gemini API chưa được cấu hình.",
            "related_tags": ["gemini-config"],
            "source": "config_error",
            "error": "Không tìm thấy GEMINI_API_KEY.",
        }
    if not transcript.strip():
        return {
            "problem_summary": "Hội thoại đang chọn không có nội dung để phân tích.",
            "action_recommendations": ["Kiểm tra conversation_id và dữ liệu CSV."],
            "knowledge_extraction": "Không có transcript.",
            "related_tags": ["empty-transcript"],
            "source": "input_error",
            "error": "Transcript rỗng.",
        }

    fallback = static_conversation_insights(misconceptions)
    payload = {
        "systemInstruction": {
            "parts": [
                {"text": "You convert tutoring transcripts into compact JSON insights for teachers."}
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": build_gemini_prompt(conversation_id, transcript, friction_label, severity_label, topic)}
                ],
            }
        ],
        "generationConfig": {
            # Gemini 3.5 no longer needs the deprecated sampling setting here.
            "responseMimeType": "application/json",
            "responseSchema": GEMINI_INSIGHT_SCHEMA,
            "maxOutputTokens": 1400,
        },
    }
    request = urllib.request.Request(
        GEMINI_API_URL_TEMPLATE.format(model=model),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
        data = json.loads(response_body)
        text = extract_text_from_gemini_response(data)
        if not text:
            raise ValueError("Gemini response không có phần text hiển thị.")
        parsed = parse_gemini_json(text)
        result = normalize_conversation_insights(parsed, fallback)
        result["model"] = model
        return result
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        error_text = f"HTTP {exc.code}: {detail[:600]}"
    except urllib.error.URLError as exc:
        error_text = f"Không kết nối được Gemini API: {exc.reason}"
    except (json.JSONDecodeError, TimeoutError, ValueError) as exc:
        error_text = str(exc)
    except Exception as exc:
        error_text = f"Lỗi Gemini không xác định: {type(exc).__name__}: {exc}"

    # Do not silently pretend that fixed demo text came from Gemini. The error is
    # now visible in the UI and the four cards clearly show analysis failure.
    return {
        "problem_summary": "Gemini đã được gọi nhưng kết quả chưa thể đưa vào giao diện.",
        "action_recommendations": [
            "Mở phần Chi tiết lỗi Gemini bên dưới để xem response thực tế.",
            "Sau khi sửa cấu hình, tải lại trang để chạy lại phân tích.",
        ],
        "knowledge_extraction": "Không sử dụng nội dung demo cố định vì lần gọi Gemini này thất bại.",
        "related_tags": ["gemini-error", model],
        "source": "api_error",
        "error": error_text[:900],
        "model": model,
    }


def html_copy(value: str) -> str:
    return html.escape(str(value)).replace("\n", "<br>")


def render(pipeline_mode: str = "Static demo") -> None:
    inject_styles()
    uploaded = None

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
                f'<span style="color:#8F96AA;font-size:13px;margin-left:10px;">'
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
        search = st.text_input("Tìm kiếm…", label_visibility="collapsed", placeholder="🔎 Tìm kiếm…", key="conversation_search")
    
        filtered = summaries.copy()
        if mode_filter != "Tất cả mức độ":
            filtered = filtered[filtered["friction_type"] == mode_filter]
        if search:
            filtered = filtered[
                filtered["snippet"].str.contains(search, case=False, na=False)
                | filtered["conversation_id"].str.contains(search, case=False, na=False)
            ]
    
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
                                <span class="badge" style="color:{fg};background:{bg};font-size:11px;">{label}</span>
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
    
            selected_messages = df[df["conversation_id"] == st.session_state.selected_conv].sort_values("_row_order")
            transcript_for_model = build_transcript_for_model(selected_messages)
            misconceptions = sel_row["misconceptions"] if isinstance(sel_row["misconceptions"], list) else []
            gemini_key = get_gemini_api_key()
            gemini_model = get_gemini_model()
            conv_id = str(st.session_state.selected_conv)
            cache_seed = "|".join(
                [conv_id, gemini_model, gemini_key_fingerprint(gemini_key), transcript_for_model]
            )
            insight_cache_key = "gemini_result_" + hashlib.sha256(
                cache_seed.encode("utf-8")
            ).hexdigest()[:20]

            if insight_cache_key not in st.session_state:
                with st.spinner("Đang phân tích hội thoại bằng Gemini..."):
                    st.session_state[insight_cache_key] = get_conversation_insights(
                        conv_id,
                        transcript_for_model,
                        friction_label,
                        severity_label,
                        str(sel_row["day_code"]),
                        misconceptions,
                        gemini_key_fingerprint(gemini_key),
                        gemini_model,
                    )
            insights = st.session_state[insight_cache_key]

            if insights.get("source") != "gemini":
                st.error("Gemini chưa trả được dữ liệu hợp lệ cho bốn khung bên dưới.")
                with st.expander("Chi tiết lỗi Gemini", expanded=True):
                    st.code(insights.get("error", "Không có chi tiết lỗi."), language="text")
    
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
    
            # Dynamic insight cards. Gemini fills these when GEMINI_API_KEY is set;
            # otherwise the app keeps the static fallback so the demo never breaks.
            with st.container(border=True, key="summary_card", gap="small"):
                st.markdown('<div class="card-title">📝 Tóm tắt vấn đề</div>', unsafe_allow_html=True)
                st.markdown(
                    f"<div class='analysis-copy'>{html_copy(insights.get('problem_summary', ''))}</div>",
                    unsafe_allow_html=True,
                )
    
            with st.container(border=True, key="recommendation_card", gap="small"):
                st.markdown(
                    '<div class="card-title" style="color:#C76A25;">💡 Khuyến nghị hành động</div>',
                    unsafe_allow_html=True,
                )
                for rec in insights.get("action_recommendations", []):
                    st.markdown(
                        f"<div class='analysis-copy'>• {html_copy(rec)}</div>",
                        unsafe_allow_html=True,
                    )
                st.button("Xem gợi ý chi tiết →", key="rec_btn")
    
            with st.container(border=True, key="knowledge_card", gap="small"):
                st.markdown(
                    '<div class="card-title" style="color:#6747EA;">📚 Trích xuất kiến thức</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='analysis-copy'>{html_copy(insights.get('knowledge_extraction', ''))}</div>",
                    unsafe_allow_html=True,
                )
    
            with st.container(border=True, key="tags_card", gap="small"):
                st.markdown('<div class="card-title">🏷️ Tag liên quan</div>', unsafe_allow_html=True)
                tags_html = "".join(
                    f'<span class="tag-pill">{html_copy(tag)}</span>' for tag in insights.get("related_tags", [])
                )
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