from __future__ import annotations

import streamlit as st

import conversations
import dashboard
import report
from shared_taskbar import get_active_page, render_taskbar, taskbar_css


st.set_page_config(
    page_title="AI Learning Analytics Copilot",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def render_placeholder(page: str) -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #111528;
            --border: #E8EBF3;
            --canvas: #F6F7FB;
            --mock-sidebar-width: 144px;
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
        .block-container {
            width: min(1100px, calc(100vw - var(--mock-sidebar-width)));
            max-width: min(1100px, calc(100vw - var(--mock-sidebar-width)));
            margin-left: var(--mock-sidebar-width) !important;
            margin-right: 0;
            padding: 1.25rem 18px 2rem;
        }
        .page-title {
            color: var(--ink);
            display: inline-block;
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 12px;
        }
        @media (min-width: 1350px) {
            :root { --mock-sidebar-width: 154px; }
        }
        @media (max-width: 1100px) {
            :root { --mock-sidebar-width: 122px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<style>" + taskbar_css("fixed") + "</style>", unsafe_allow_html=True)
    render_taskbar(page, "Static demo")
    st.markdown(f'<span class="page-title">{page.title()}</span>', unsafe_allow_html=True)
    st.info("Màn này chưa được triển khai. Thêm page trong main.py và item trong shared_taskbar.py khi cần.")


def main() -> None:
    page = get_active_page(default="dashboard")

    if page == "dashboard":
        dashboard.render()
    elif page == "conversations":
        conversations.render()
    elif page == "reports":
        report.render()
    else:
        render_placeholder(page)


if __name__ == "__main__":
    main()