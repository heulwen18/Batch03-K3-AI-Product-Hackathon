from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Literal

import streamlit as st


@dataclass(frozen=True)
class TaskbarItem:
    page: str
    label: str
    icon: str


TASKBAR_ITEMS: tuple[TaskbarItem, ...] = (
    TaskbarItem("dashboard", "Live Dashboard", "✦"),
    TaskbarItem("conversations", "Conversations", "◉"),
    TaskbarItem("reports", "Reports", "▧"),
    TaskbarItem("settings", "Settings", "⚙"),
)
KNOWN_PAGES = frozenset(item.page for item in TASKBAR_ITEMS)


def normalize_page(page: object, default: str = "conversations") -> str:
    """Normalize a query-param page value into a taskbar page slug."""
    if isinstance(page, list):
        page = page[0] if page else default
    slug = str(page or default).strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "live": "dashboard",
        "live-dashboard": "dashboard",
        "conversation": "conversations",
    }
    slug = aliases.get(slug, slug)
    return slug if slug in KNOWN_PAGES else default


def get_active_page(default: str = "conversations") -> str:
    return normalize_page(st.query_params.get("page", default), default=default)


def taskbar_html(active_page: str, pipeline_mode: str = "Static demo") -> str:
    active_page = normalize_page(active_page)
    nav_items = []
    for item in TASKBAR_ITEMS:
        active_class = ' class="active"' if item.page == active_page else ""
        nav_items.append(
            f'<a{active_class} href="?page={item.page}" target="_self">'
            f'<span>{html.escape(item.icon)}</span>{html.escape(item.label)}</a>'
        )
    nav_html = "\n        ".join(nav_items)
    safe_mode = html.escape(pipeline_mode)
    return f"""
    <aside class="mock-sidebar" aria-label="AI Learning Analytics Copilot navigation">
      <div class="brand">
        <div class="brand-mark"><span></span><i></i><b></b></div>
        <div><strong>AI Learning</strong><small>Analytics Copilot</small></div>
      </div>
      <nav class="mock-nav" aria-label="Main navigation">
        {nav_html}
      </nav>
      <div class="sidebar-fill"></div>
      <div class="processing-card">
        <strong><i></i> Live Processing</strong>
        <p>Đang xử lý dữ liệu<br><span>{safe_mode}</span></p>
        <small>Sẵn sàng nhận batch mới</small>
      </div>
      <div class="profile">
        <div class="avatar">A</div>
        <div><strong>GV. Minh Anh</strong><small>Giảng viên</small></div>
        <span>⌄</span>
      </div>
    </aside>
    """


def render_taskbar(active_page: str, pipeline_mode: str = "Static demo") -> None:
    st.markdown(
        f'<div class="taskbar-mount">{taskbar_html(active_page, pipeline_mode)}</div>',
        unsafe_allow_html=True,
    )


def taskbar_css(position: Literal["fixed", "sticky"] = "fixed") -> str:
    if position == "sticky":
        placement = """
        position: sticky;
        top: 0;
        width: var(--mock-sidebar-width, 144px);
        """
    else:
        placement = """
        position: fixed;
        left: 0;
        top: 0;
        z-index: 1000;
        width: var(--mock-sidebar-width, 144px);
        """
    return f"""
    .taskbar-mount {{
        height: 0;
        overflow: visible;
    }}
    .mock-sidebar {{
        {placement}
        height: 100vh;
        display: flex;
        flex-direction: column;
        padding: 12px 11px 11px;
        background: #FFFFFF;
        border-right: 1px solid var(--border, #E8EBF3);
    }}
    .brand {{
        height: 43px;
        display: flex;
        align-items: center;
        gap: 7px;
        padding: 0 2px;
        margin-bottom: 12px;
    }}
    .brand strong, .brand small {{ display: block; line-height: 1.2; }}
    .brand strong {{ font-size: 8px; color: #202436; font-weight: 800; }}
    .brand small {{ font-size: 7px; color: #737A91; margin-top: 1px; font-weight: 650; }}
    .brand-mark {{
        width: 20px;
        height: 20px;
        flex: 0 0 20px;
        border-radius: 50%;
        background: linear-gradient(145deg, #8568FF, #5C3ADE);
        position: relative;
        box-shadow: 0 5px 12px #7557F633;
    }}
    .brand-mark span, .brand-mark i, .brand-mark b {{
        position: absolute; width: 3px; height: 3px; border-radius: 50%;
        background: white;
    }}
    .brand-mark span {{ left: 5px; top: 10px; }}
    .brand-mark i {{ left: 10px; top: 5px; }}
    .brand-mark b {{ right: 5px; top: 12px; }}
    .brand-mark:after {{
        content: ""; position: absolute; left: 6px; top: 7px; width: 9px;
        height: 6px; border: 1px solid #FFFFFFAA; transform: rotate(-9deg);
    }}
    .mock-nav {{ display: grid; gap: 4px; }}
    .mock-nav a {{
        height: 27px;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 9px;
        border-radius: 6px;
        color: #34394C;
        text-decoration: none;
        font-size: 8px;
        font-weight: 750;
    }}
    .mock-nav a span {{
        width: 11px;
        display: inline-grid;
        place-items: center;
        color: #141827;
        font-size: 9px;
    }}
    .mock-nav a.active {{
        color: #6747EA;
        background: #F0ECFF;
    }}
    .mock-nav a.active span {{ color: #6747EA; }}
    .sidebar-fill {{ flex: 1; min-height: 170px; }}
    .processing-card {{
        border: 1px solid #E8EAF0;
        background: #FAFBFD;
        border-radius: 8px;
        padding: 10px;
        margin: 0 0 10px;
    }}
    .processing-card strong {{ display: block; font-size: 8px; color: #5D6476; }}
    .processing-card strong i {{
        display: inline-block; width: 6px; height: 6px; margin-right: 6px;
        border-radius: 50%; background: #23C980; box-shadow: 0 0 0 3px #23C98018;
    }}
    .processing-card p {{ margin: 7px 0; font-size: 7.5px; color: #747A8D; line-height: 1.45; }}
    .processing-card p span {{ color: #25A36B; font-weight: 700; }}
    .processing-card small {{ font-size: 6.5px; color: #A0A5B6; }}
    .profile {{
        display: flex; align-items: center; gap: 7px; padding: 10px 0 2px;
        border-top: 1px solid #EFF0F5;
    }}
    .profile .avatar {{
        width: 24px; height: 24px; display: grid; place-items: center;
        color: white; background: #6A52DB; border-radius: 50%; font-size: 9px; font-weight: 800;
    }}
    .profile div:nth-child(2) {{ flex: 1; }}
    .profile strong, .profile small {{ display: block; }}
    .profile strong {{ font-size: 7.5px; }}
    .profile small {{ font-size: 6.5px; color: #9AA0B3; margin-top: 1px; }}
    .profile > span {{ color: #A3A7B5; font-size: 9px; }}
    """