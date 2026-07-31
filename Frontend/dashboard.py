from __future__ import annotations

import base64
import html
import importlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Iterable

import pandas as pd
import streamlit as st

from shared_taskbar import get_active_page, taskbar_css, taskbar_html


APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = (
    APP_DIR
    / "data"
    / "vlearn-pack"
    / "chatlog"
    / "chat_history_anonymized_for_hackathon.csv"
)

COLORS = {
    "Learning Difficulty": "#7C5CFC",
    "Tutor Limitation": "#FF9B50",
    "Off-topic / Drift": "#5B8DEF",
    "Normal / No issue": "#45C98B",
}

LABELS = {
    "Learning Difficulty": "Learning Difficulty",
    "Tutor Limitation": "Tutor Limitation",
    "Off-topic / Drift": "Off-topic / Drift",
    "Normal / No issue": "Normal / No issue",
}

ICONS = {
    "Learning Difficulty": "◆",
    "Tutor Limitation": "▲",
    "Off-topic / Drift": "↗",
    "Normal / No issue": "✓",
}

SEVERITY = {
    "Normal / No issue": 0,
    "Off-topic / Drift": 1,
    "Learning Difficulty": 2,
    "Tutor Limitation": 3,
}

STATIC_TOTALS = {
    "Learning Difficulty": 100,
    "Tutor Limitation": 43,
    "Off-topic / Drift": 21,
    "Normal / No issue": 192,
}

TOPIC_PATTERNS = {
    "Prompt Engineering": r"\bprompt\b|nhắc lệnh",
    "RAG Retrieval": r"\brag\b|retriev|truy xuất|tìm tài liệu",
    "Agent Memory": r"\bagent\b|\bmemory\b|bộ nhớ|react",
    "Context Window": r"\bcontext\b|ngữ cảnh|cửa sổ",
    "Tool Usage": r"\btool\b|công cụ|function call",
    "Function Calling": r"function calling|gọi hàm|structured output|json",
    "Transformer": r"transformer|attention|embedding",
    "Tokenization": r"\btoken\b|tokenization|tách từ",
}


@dataclass(frozen=True)
class PipelineResult:
    turns: pd.DataFrame
    mode: str


@st.cache_data(show_spinner=False)
def build_static_turns() -> pd.DataFrame:
    """Create a deterministic UI dataset without reading the future data pack."""
    anchor = pd.Timestamp("2026-07-30 10:32:45", tz="Asia/Bangkok")
    categories: list[str] = []
    remaining = STATIC_TOTALS.copy()
    category_order = list(STATIC_TOTALS)
    while sum(remaining.values()):
        for category in category_order:
            if remaining[category] > 0:
                categories.append(category)
                remaining[category] -= 1

    friction_topics = (
        ["Context Window"] * 44
        + ["RAG Retrieval"] * 36
        + ["Agent Memory"] * 29
        + ["Prompt Engineering"] * 23
        + ["Tool Usage"] * 17
        + ["Function Calling"] * 10
        + ["Other"] * 5
    )
    normal_topics = (
        ["RAG Retrieval"] * 52
        + ["Context Window"] * 42
        + ["Agent Memory"] * 36
        + ["Prompt Engineering"] * 28
        + ["Tool Usage"] * 22
        + ["Function Calling"] * 12
    )
    examples = {
        "Learning Difficulty": [
            ("Mình vẫn chưa hiểu Context Window khác Memory như thế nào?", "Giảng lại bằng ví dụ trực quan và so sánh từng khái niệm."),
            ("Tại sao Agent cần gọi tool thay vì tự trả lời?", "Giải thích theo từng bước và đưa một ví dụ ngắn."),
            ("Bạn cho mình thêm ví dụ về Prompt Engineering được không?", "Đưa thêm ví dụ phù hợp với nội dung bài học."),
        ],
        "Tutor Limitation": [
            ("Tóm tắt nội dung quan trọng nhất trong slide này.", "Xin lỗi, tôi chưa tìm thấy nội dung cụ thể trong tài liệu hiện có."),
            ("Phần RAG này nằm ở bài giảng nào?", "Tôi không tìm thấy tài liệu phù hợp để trả lời chính xác."),
            ("Giải thích đoạn được chọn ở trang 19.", "Nguồn hiện tại chưa cung cấp đủ thông tin cho đoạn này."),
        ],
        "Off-topic / Drift": [
            ("Hello bạn", "Chào bạn! Hãy gửi câu hỏi liên quan đến bài học nhé."),
            ("Bạn là model nào?", "Mình là trợ lý học tập của khóa học."),
            ("test", "Mình đã sẵn sàng hỗ trợ nội dung học tập."),
        ],
        "Normal / No issue": [
            ("Hãy nhắc lại ba bước chính của quy trình RAG.", "RAG gồm truy xuất, bổ sung ngữ cảnh và sinh câu trả lời."),
            ("Agent Memory dùng để làm gì?", "Memory giúp agent lưu và sử dụng lại thông tin cần thiết."),
            ("Cho mình định nghĩa ngắn về Function Calling.", "Function Calling cho phép mô hình gọi hàm theo schema xác định."),
        ],
    }
    reasons = {
        "Learning Difficulty": "Học viên cần thêm giải thích, ví dụ hoặc so sánh khái niệm",
        "Tutor Limitation": "Tutor chưa tìm được nội dung hoặc nguồn phù hợp",
        "Off-topic / Drift": "Nội dung ngoài mục tiêu học tập",
        "Normal / No issue": "Hội thoại được xử lý bình thường",
    }
    confidence = {
        "Learning Difficulty": 0.89,
        "Tutor Limitation": 0.95,
        "Off-topic / Drift": 0.92,
        "Normal / No issue": 0.86,
    }

    records = []
    friction_index = 0
    normal_index = 0
    for index, category in enumerate(categories, start=1):
        student_text, tutor_text = examples[category][(index - 1) % len(examples[category])]
        timestamp = anchor - pd.Timedelta(seconds=(index - 1) * 5)
        if category == "Normal / No issue":
            topic = normal_topics[normal_index % len(normal_topics)]
            normal_index += 1
        else:
            topic = friction_topics[friction_index % len(friction_topics)]
            friction_index += 1
        records.append(
            {
                "conversation_id": f"C{index:04d}",
                "user_id": f"U{((index - 1) % 192) + 1:04d}",
                "day_code": "AI Agent - Week 4",
                "turn_id": f"T{index:04d}",
                "message_created_at": timestamp,
                "llm_call_count": 2 + index % 3,
                "models_used": "demo-static",
                "total_input_tokens": 900 + index * 3,
                "total_output_tokens": 90 + index % 120,
                "avg_latency_ms": 1100 + index % 900,
                "student_content": student_text,
                "tutor_content": tutor_text,
                "move_used": "review_concept",
                "citations": "[]",
                "rating": "down" if category == "Tutor Limitation" and index % 5 == 0 else "",
                "asked_check_question": False,
                "category": category,
                "reason": reasons[category],
                "confidence": confidence[category],
                "topic": topic,
                "date": timestamp.date(),
            }
        )
    return pd.DataFrame.from_records(records).sort_values(
        "message_created_at", ascending=False
    ).reset_index(drop=True)


def _contains(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def _safe_text(value: object, limit: int = 170) -> str:
    if value is None or pd.isna(value):
        return ""
    compact = re.sub(r"\s+", " ", str(value)).strip()
    if len(compact) > limit:
        compact = compact[: limit - 1].rstrip() + "…"
    return html.escape(compact)


def _extract_topic(text: str) -> str:
    for topic, pattern in TOPIC_PATTERNS.items():
        if _contains(text, pattern):
            return topic
    return "Other"


def _fallback_classify(row: pd.Series) -> tuple[str, str, float]:
    student = str(row.get("student_content", "") or "").lower()
    tutor = str(row.get("tutor_content", "") or "").lower()
    rating = str(row.get("rating", "") or "").lower()
    move = str(row.get("move_used", "") or "").lower()

    tutor_failure = _contains(
        tutor,
        r"không tìm thấy|không có (?:đủ )?(?:nội dung|thông tin|tài liệu)"
        r"|xin lỗi.{0,45}(?:không thể|chưa thể)|không được cung cấp",
    )
    drift = (
        len(re.sub(r"\W+", "", student)) <= 5
        or _contains(
            student,
            r"\b(?:hello|hi|test|bye)\b|chào bạn|model nào|đẹp trai|"
            r"bao nhiêu tuổi|kể chuyện|thời tiết",
        )
    )
    difficulty = (
        rating == "down"
        or move == "give_direct_answer"
        or _contains(
            student,
            r"không hiểu|chưa hiểu|là gì|giải thích|tại sao|vì sao|"
            r"ví dụ|khác nhau|phân biệt|như thế nào|hiểu đúng|có phải",
        )
    )

    if tutor_failure:
        return "Tutor Limitation", "Tutor không tìm được nội dung hoặc nguồn phù hợp", 0.94
    if drift:
        return "Off-topic / Drift", "Tín hiệu chào hỏi, thử hệ thống hoặc ngoài mục tiêu học", 0.91
    if difficulty:
        return "Learning Difficulty", "Học viên cần giải thích, ví dụ hoặc câu trả lời trực tiếp", 0.82
    return "Normal / No issue", "Chưa phát hiện tín hiệu friction đủ mạnh", 0.76


@st.cache_data(show_spinner=False)
def load_turns(data_path: str, modified_at: float) -> pd.DataFrame:
    del modified_at
    raw = pd.read_csv(data_path)
    raw["message_created_at"] = pd.to_datetime(
        raw["message_created_at"], errors="coerce", utc=True
    )

    base_cols = [
        "conversation_id",
        "user_id",
        "day_code",
        "turn_id",
        "message_created_at",
        "llm_call_count",
        "models_used",
        "total_input_tokens",
        "total_output_tokens",
        "avg_latency_ms",
    ]
    students = (
        raw.loc[raw["role"].eq("student"), base_cols + ["content"]]
        .rename(columns={"content": "student_content"})
        .drop_duplicates("turn_id")
    )
    tutor_cols = [
        "turn_id",
        "content",
        "move_used",
        "citations",
        "rating",
        "asked_check_question",
    ]
    tutors = (
        raw.loc[raw["role"].eq("tutor"), tutor_cols]
        .rename(columns={"content": "tutor_content"})
        .drop_duplicates("turn_id")
    )
    turns = students.merge(tutors, on="turn_id", how="left")
    turns["message_created_at"] = turns["message_created_at"].dt.tz_convert(
        "Asia/Bangkok"
    )

    classified = turns.apply(_fallback_classify, axis=1, result_type="expand")
    classified.columns = ["category", "reason", "confidence"]
    turns = pd.concat([turns, classified], axis=1)
    turns["topic"] = (
        turns["student_content"].fillna("")
        + " "
        + turns["tutor_content"].fillna("")
    ).map(_extract_topic)
    turns["date"] = turns["message_created_at"].dt.date
    return turns.sort_values("message_created_at", ascending=False).reset_index(drop=True)


def apply_pipeline_adapter(turns: pd.DataFrame) -> PipelineResult:
    """
    Optional integration point for the team's real pipeline.

    If ``codebase.pipeline.enrich_dashboard_turns`` exists, it receives a copy of
    the paired-turn DataFrame and must return a DataFrame containing at least
    ``turn_id`` and ``category``. Optional columns: ``reason``, ``confidence``,
    and ``topic``. The UI keeps working with the transparent rule-based fallback
    when that module has not been implemented yet.
    """
    try:
        module = importlib.import_module("codebase.pipeline")
        enrich = getattr(module, "enrich_dashboard_turns")
    except (ModuleNotFoundError, AttributeError):
        return PipelineResult(turns=turns, mode="Rule-based fallback")

    try:
        enriched = enrich(turns.copy())
        if not isinstance(enriched, pd.DataFrame):
            raise TypeError("Pipeline must return a pandas DataFrame.")
        required = {"turn_id", "category"}
        if not required.issubset(enriched.columns):
            raise ValueError("Pipeline output is missing turn_id/category.")
        valid_categories = set(COLORS)
        if not set(enriched["category"].dropna()).issubset(valid_categories):
            raise ValueError("Pipeline returned an unsupported category.")

        replace_cols = [
            column
            for column in ("category", "reason", "confidence", "topic")
            if column in enriched.columns
        ]
        merged = turns.drop(columns=replace_cols, errors="ignore").merge(
            enriched[["turn_id", *replace_cols]].drop_duplicates("turn_id"),
            on="turn_id",
            how="left",
        )
        return PipelineResult(turns=merged, mode="AI pipeline")
    except Exception as exc:  # keep the demo usable while surfacing the contract error
        st.warning(f"Pipeline riêng chưa dùng được; đang dùng fallback. Chi tiết: {exc}")
        return PipelineResult(turns=turns, mode="Rule-based fallback")


def conversation_view(turns: pd.DataFrame) -> pd.DataFrame:
    if turns.empty:
        return pd.DataFrame(
            columns=[
                "conversation_id",
                "category",
                "topic",
                "message_created_at",
                "turn_count",
            ]
        )

    ordered = turns.assign(_severity=turns["category"].map(SEVERITY).fillna(0))
    dominant = (
        ordered.sort_values(
            ["conversation_id", "_severity", "message_created_at"],
            ascending=[True, False, False],
        )
        .drop_duplicates("conversation_id")
        .set_index("conversation_id")
    )
    counts = turns.groupby("conversation_id").size().rename("turn_count")
    latest = turns.groupby("conversation_id")["message_created_at"].max()
    result = dominant[["category", "topic", "student_content", "reason"]].join(
        [counts, latest.rename("latest_at")]
    )
    return result.reset_index()


def filter_range(turns: pd.DataFrame, label: str) -> pd.DataFrame:
    if turns.empty or label == "Toàn bộ dữ liệu":
        return turns
    windows = {
        "30 phút gần nhất": pd.Timedelta(minutes=30),
        "1 giờ gần nhất": pd.Timedelta(hours=1),
        "24 giờ gần nhất": pd.Timedelta(days=1),
        "7 ngày gần nhất": pd.Timedelta(days=7),
    }
    anchor = turns["message_created_at"].max()
    return turns.loc[turns["message_created_at"] >= anchor - windows[label]].copy()


def _sparkline(values: Iterable[float], color: str) -> str:
    values = [float(value) for value in values]
    if not values:
        values = [0, 0]
    if len(values) == 1:
        values = [values[0], values[0]]
    width, height, pad = 150, 34, 3
    lo, hi = min(values), max(values)
    spread = max(hi - lo, 1)
    points: list[tuple[float, float]] = []
    for index, value in enumerate(values):
        x = pad + index * (width - 2 * pad) / (len(values) - 1)
        y = height - pad - (value - lo) * (height - 2 * pad) / spread
        points.append((x, y))
    baseline = height - pad
    line_path = _smooth_line_path(points)
    area_path = _smooth_area_path(points, baseline)
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        f'aria-hidden="true"><path d="{area_path}" fill="{color}" opacity=".12"/>'
        f'<path d="{line_path}" fill="none" stroke="{color}" '
        f'stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def _smooth_line_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    return (
        f"M {points[0][0]:.1f} {points[0][1]:.1f} "
        + " ".join(_smooth_curve_commands(points))
    ).strip()


def _smooth_curve_commands(points: list[tuple[float, float]]) -> list[str]:
    commands = []
    for index in range(1, len(points)):
        prev_x, prev_y = points[index - 1]
        x, y = points[index]
        dx = x - prev_x
        commands.append(
            f"C {prev_x + dx * .45:.1f} {prev_y:.1f}, "
            f"{x - dx * .45:.1f} {y:.1f}, {x:.1f} {y:.1f}"
        )
    return commands


def _smooth_area_path(points: list[tuple[float, float]], baseline: float) -> str:
    if not points:
        return ""
    return (
        f"M {points[0][0]:.1f} {baseline:.1f} "
        f"L {points[0][0]:.1f} {points[0][1]:.1f} "
        f"{' '.join(_smooth_curve_commands(points))} "
        f"L {points[-1][0]:.1f} {baseline:.1f} Z"
    )


def _bucketed_counts(
    turns: pd.DataFrame,
    categories: Iterable[str] | None = None,
    *,
    bucket_count: int = 10,
    cumulative: bool = True,
) -> pd.DataFrame:
    labels = list(categories) if categories is not None else ["__all__"]
    if turns.empty:
        return pd.DataFrame({label: [0] * bucket_count for label in labels})

    frame = turns.sort_values("message_created_at").copy()
    start = frame["message_created_at"].min()
    end = frame["message_created_at"].max()
    if pd.isna(start) or pd.isna(end) or start == end:
        bucket = pd.Series([bucket_count - 1] * len(frame), index=frame.index)
    else:
        span = max((end - start).total_seconds(), 1)
        bucket = (
            ((frame["message_created_at"] - start).dt.total_seconds() / span)
            * (bucket_count - 1)
        ).round().clip(0, bucket_count - 1).astype(int)

    frame["_bucket"] = bucket
    if categories is None:
        counts = frame.groupby("_bucket").size().reindex(range(bucket_count), fill_value=0)
        result = counts.to_frame("__all__")
    else:
        result = (
            frame.groupby(["_bucket", "category"])
            .size()
            .unstack(fill_value=0)
            .reindex(index=range(bucket_count), fill_value=0)
            .reindex(columns=labels, fill_value=0)
        )
    return result.cumsum() if cumulative else result


def _metric_card(
    title: str,
    value: str,
    subtitle: str,
    color: str,
    icon: str,
    spark_values: Iterable[float],
) -> str:
    return f"""
    <article class="metric-card">
      <div class="metric-head">
        <span class="metric-icon" style="color:{color};background:{color}16">{icon}</span>
        <span>{html.escape(title)}</span>
      </div>
      <div class="metric-value" style="color:{color if '%' in value else '#141827'}">{value}</div>
      <div class="metric-sub">{html.escape(subtitle)}</div>
      <div class="spark">{_sparkline(spark_values, color)}</div>
    </article>
    """


def _trend_svg(turns: pd.DataFrame) -> str:
    categories = [
        "Learning Difficulty",
        "Tutor Limitation",
        "Off-topic / Drift",
    ]
    if _is_static_demo_turns(turns):
        grouped = pd.DataFrame(
            {
                "Learning Difficulty": [38, 43, 49, 54, 61, 66, 70, 73, 75],
                "Tutor Limitation": [27, 29, 31, 34, 36, 38, 40, 42, 43],
                "Off-topic / Drift": [14, 15, 16, 17, 18, 19, 20, 21, 21],
            }
        )
    else:
        grouped = _bucketed_counts(turns, categories, bucket_count=9, cumulative=True)

    width, height = 850, 250
    left, right, top, bottom = 48, 16, 18, 36
    plot_w, plot_h = width - left - right, height - top - bottom
    max_value = 100 if _is_static_demo_turns(turns) else max(
        int(grouped[categories].to_numpy().max()), 100, 1
    )
    grid = []
    for index in range(5):
        y = top + plot_h * index / 4
        value = round(max_value * (1 - index / 4))
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" '
            f'stroke="#EBEDF4" stroke-width="1"/>'
            f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" '
            f'fill="#9AA0B5" font-size="14">{value}</text>'
        )

    area_elements = []
    line_elements = []
    for category in reversed(categories):
        values = grouped[category].tolist()
        if len(values) == 1:
            values = [values[0], values[0]]
        points: list[tuple[float, float]] = []
        for index, value in enumerate(values):
            x = left + index * plot_w / (len(values) - 1)
            y = top + plot_h - value * plot_h / max_value
            points.append((x, y))
        color = COLORS[category]
        area_elements.append(
            f'<path d="{_smooth_area_path(points, top + plot_h)}" '
            f'fill="{color}" opacity=".12"/>'
        )
        line_elements.append(
            f'<path d="{_smooth_line_path(points)}" fill="none" stroke="{color}" '
            f'stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    labels = []
    raw_labels = []
    if turns.empty:
        raw_labels = [""] * len(grouped.index)
    else:
        frame = turns.sort_values("message_created_at")
        start = frame["message_created_at"].min()
        end = frame["message_created_at"].max()
        for index in grouped.index:
            if start == end:
                label_time = end
            else:
                label_time = start + (end - start) * (int(index) / max(len(grouped.index) - 1, 1))
            raw_labels.append(label_time.strftime("%H:%M"))
    label_indexes = sorted(set([0, len(raw_labels) // 4, len(raw_labels) // 2, len(raw_labels) * 3 // 4, len(raw_labels) - 1]))
    for index in label_indexes:
        x = left if len(raw_labels) == 1 else left + index * plot_w / (len(raw_labels) - 1)
        labels.append(
            f'<text x="{x:.1f}" y="{height-10}" text-anchor="middle" '
            f'fill="#9AA0B5" font-size="14">{html.escape(raw_labels[index])}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="trend-svg" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none">{"".join(grid)}{"".join(area_elements)}'
        f'{"".join(line_elements)}'
        f'{"".join(labels)}</svg>'
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img class="trend-svg" alt="Learning friction over time chart" src="data:image/svg+xml;base64,{encoded}" />'


def _is_static_demo_turns(turns: pd.DataFrame) -> bool:
    if turns.empty or len(turns) != sum(STATIC_TOTALS.values()):
        return False
    counts = turns["category"].value_counts().to_dict()
    return all(int(counts.get(category, -1)) == total for category, total in STATIC_TOTALS.items())


def _legend() -> str:
    items = []
    for category in (
        "Learning Difficulty",
        "Tutor Limitation",
        "Off-topic / Drift",
    ):
        items.append(
            f'<span><i style="background:{COLORS[category]}"></i>{LABELS[category]}</span>'
        )
    return "".join(items)


def _top_issues(turns: pd.DataFrame) -> str:
    friction = turns.loc[turns["category"].ne("Normal / No issue")]
    counts = friction["topic"].value_counts().sort_values(ascending=False).head(5)
    if counts.empty:
        counts = pd.Series({"Chưa có tín hiệu": 0})
    maximum = max(int(counts.max()), 1)
    rows = []
    for index, (topic, count) in enumerate(counts.items(), start=1):
        percent = int(round(count / maximum * 100))
        rows.append(
            f"""
            <div class="issue-row">
              <span class="rank">{index}</span>
              <span class="issue-name">{html.escape(str(topic))}</span>
              <span class="issue-bar"><i style="width:{percent}%"></i></span>
              <span class="issue-count">{int(count)} lượt</span>
            </div>
            """
        )
    return "".join(rows)


def _recent_alerts(turns: pd.DataFrame, limit: int = 4) -> str:
    alerts = turns.loc[turns["category"].ne("Normal / No issue")].head(limit)
    if alerts.empty:
        return '<div class="empty-note">Chưa có cảnh báo trong khoảng thời gian này.</div>'
    rows = []
    for _, row in alerts.iterrows():
        category = str(row["category"])
        color = COLORS[category]
        timestamp = row["message_created_at"].strftime("%H:%M")
        rows.append(
            f"""
            <div class="alert-row">
              <span class="alert-dot" style="background:{color}"></span>
              <div>
                <strong>{html.escape(category)} detected</strong>
                <p>{_safe_text(row.get("reason"), 78)}</p>
                <a> Xem chi tiết →</a>
              </div>
              <time>{timestamp}</time>
            </div>
            """
        )
    return "".join(rows)


def _action_recommendation(turns: pd.DataFrame) -> str:
    friction = turns.loc[turns["category"].ne("Normal / No issue")]
    topic = "Context Window"
    if not friction.empty:
        topic_counts = friction["topic"].value_counts()
        if not topic_counts.empty:
            topic = str(topic_counts.index[0])
    return f"""
    <article class="action-card">
      <div class="action-icon">!</div>
      <div class="action-copy">
        <strong>Khuyến nghị hành động</strong>
        <p>Kiểm tra các đoạn giải thích về “{html.escape(topic)}” và bổ sung ví dụ trực quan.</p>
      </div>
      <button class="action-button">Xem gợi ý chi tiết +</button>
    </article>
    """


def _recent_conversations(turns: pd.DataFrame, limit: int = 5) -> str:
    if turns.empty:
        return '<div class="empty-note">Chưa có hội thoại trong khoảng thời gian này.</div>'
    rows = []
    for _, row in turns.head(limit).iterrows():
        category = str(row["category"])
        timestamp = row["message_created_at"].strftime("%H:%M")
        rows.append(
            f"""
            <div class="conversation-row">
              <span class="time-badge">{timestamp}</span>
              <div class="conversation-copy">
                <p>{_safe_text(row.get("student_content"), 112)}</p>
                <span style="color:{COLORS[category]};background:{COLORS[category]}12">
                  {html.escape(category)}
                </span>
              </div>
              <span class="topic-pill">{html.escape(str(row.get("topic", "Other")))}</span>
            </div>
            """
        )
    return "".join(rows)


def _topic_map(turns: pd.DataFrame) -> str:
    palette = [
        ("#FFE6DA", "#9D4C2C"),
        ("#FFE8D9", "#A55A34"),
        ("#DDF5E9", "#2D7354"),
        ("#DBE7FF", "#375A9F"),
        ("#DDF5E9", "#2D7354"),
        ("#E6EAF1", "#4B5569"),
        ("#E9E0FF", "#6547A5"),
    ]
    counts = turns["topic"].value_counts().head(7)
    if counts.empty:
        counts = pd.Series({"Chưa có dữ liệu": 0})
    total = max(int(counts.sum()), 1)
    blocks = []
    for index, (topic, count) in enumerate(counts.items()):
        background, color = palette[index % len(palette)]
        percent = count / total * 100
        blocks.append(
            f"""
            <div class="topic-block topic-{index + 1}" style="background:{background};color:{color}">
              <strong>{int(count)}</strong>
              <span>{html.escape(str(topic))}</span>
              <small>{percent:.0f}%</small>
            </div>
            """
        )
    return "".join(blocks)


def _metric_series(turns: pd.DataFrame, category: str | None = None) -> list[int]:
    if category is None:
        return _bucketed_counts(turns, None, bucket_count=12)["__all__"].tolist()
    return _bucketed_counts(turns, [category], bucket_count=12)[category].tolist()


def _dashboard_html(turns: pd.DataFrame, pipeline_mode: str) -> str:
    conversations = conversation_view(turns)
    total = len(conversations)
    counts = conversations["category"].value_counts()

    metrics = [
        (
            "Tổng cuộc hội thoại",
            f"{total:,}".replace(",", "."),
            f"{len(turns):,} lượt hỏi–đáp đã xử lý".replace(",", "."),
            "#7C5CFC",
            "◉",
            _metric_series(turns),
        )
    ]
    for category in (
        "Learning Difficulty",
        "Tutor Limitation",
        "Off-topic / Drift",
        "Normal / No issue",
    ):
        count = int(counts.get(category, 0))
        percent = 0 if total == 0 else round(count / total * 100)
        metrics.append(
            (
                category,
                f"{percent}%",
                f"{count} hội thoại",
                COLORS[category],
                ICONS[category],
                _metric_series(turns, category),
            )
        )

    metric_html = "".join(_metric_card(*metric) for metric in metrics)
    latest_time = (
        turns["message_created_at"].max().strftime("%H:%M:%S")
        if not turns.empty
        else "--:--:--"
    )
    confidence = (
        int(round(turns["confidence"].fillna(0).mean() * 100)) if not turns.empty else 0
    )
    bell_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
        '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 7-3 9h18c0-2-3-2-3-9" '
        'stroke="#5F687D" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="#5F687D" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
    )
    bell_src = "data:image/svg+xml;base64," + base64.b64encode(bell_svg.encode("utf-8")).decode("ascii")
    return dedent(
        f"""
        <section class="app-shell" aria-label="AI Learning Analytics Copilot">
          {taskbar_html("dashboard", pipeline_mode)}

          <main class="dashboard-main">
            <header class="dashboard-header">
              <div class="page-title">
                <h1>AI Agent - Week 4 <span>LIVE</span></h1>
                <p>Bắt đầu lúc 09:30 AM</p>
              </div>
              <div class="header-actions">
                <span class="clock">10:32:45 AM</span>
                <span class="time-select">Last 30 minutes <b>⌄</b></span>
                <span class="notification" aria-label="Notifications">
                  <img class="notification-icon" src="{bell_src}" alt="" />
                  <i></i>
                </span>
              </div>
            </header>

            <div class="metric-grid">{metric_html}</div>

            <div class="dashboard-grid dashboard-grid-top">
              <article class="panel trend-panel">
                <div class="panel-heading">
                  <div><h3>Learning Friction Over Time</h3><div class="legend">{_legend()}</div></div>
                  <button class="ghost-button">Xem chi tiết</button>
                </div>
                {_trend_svg(turns)}
              </article>

              <article class="panel issues-panel">
                <div class="panel-heading"><h3>Top vấn đề đang tăng</h3><button class="ghost-button">Xem tất cả</button></div>
                <div class="issue-list">{_top_issues(turns)}</div>
              </article>

              <article class="panel alerts-panel">
                <div class="panel-heading"><h3>Recent Alerts</h3><button class="ghost-button">Xem tất cả</button></div>
                <div class="alert-list">{_recent_alerts(turns)}</div>
              </article>

              {_action_recommendation(turns)}
            </div>

            <div class="dashboard-grid dashboard-grid-bottom">
              <article class="panel conversations-panel">
                <div class="panel-heading">
                  <div><h3>Các hội thoại mới nhất (Real-time)</h3></div>
                  <button class="ghost-button">Xem tất cả</button>
                </div>
                <div class="conversation-list">{_recent_conversations(turns)}</div>
              </article>

              <article class="panel topic-panel">
                <div class="panel-heading"><h3>Bản đồ chủ đề (Topic Heatmap)</h3><button class="ghost-button">Xem tất cả</button></div>
                <div class="topic-map">{_topic_map(turns)}</div>
              </article>
            </div>

            <div class="status-bar">
              <span><i></i> Hệ thống đang phân tích {len(turns):,} lượt gần nhất · {pipeline_mode}</span>
              <span>Cập nhật lần cuối {latest_time} ↗</span>
            </div>
          </main>
        </section>
        """
    ).strip()


def render_dashboard(turns: pd.DataFrame, pipeline_mode: str) -> None:
    range_label = "30 phút gần nhất"
    selected = filter_range(turns, range_label)
    if selected.empty:
        st.info("Không có dữ liệu trong khoảng đã chọn.")
    st.html(_dashboard_html(selected, pipeline_mode))


def render_conversations(turns: pd.DataFrame) -> None:
    st.markdown(
        '<div class="section-title"><h1>Conversations</h1>'
        "<p>Tra cứu từng lượt hỏi–đáp và lý do phân loại.</p></div>",
        unsafe_allow_html=True,
    )
    query = st.text_input("Tìm theo nội dung, turn ID hoặc conversation ID", "")
    categories = st.multiselect(
        "Nhóm friction", list(COLORS), default=list(COLORS), key="conversation_categories"
    )
    filtered = turns.loc[turns["category"].isin(categories)].copy()
    if query.strip():
        needle = re.escape(query.strip())
        mask = (
            filtered["student_content"].fillna("").str.contains(needle, case=False, regex=True)
            | filtered["tutor_content"].fillna("").str.contains(needle, case=False, regex=True)
            | filtered["turn_id"].fillna("").str.contains(needle, case=False, regex=True)
            | filtered["conversation_id"].fillna("").str.contains(
                needle, case=False, regex=True
            )
        )
        filtered = filtered.loc[mask]

    table = filtered[
        [
            "message_created_at",
            "conversation_id",
            "turn_id",
            "student_content",
            "category",
            "topic",
            "confidence",
        ]
    ].copy()
    table["message_created_at"] = table["message_created_at"].dt.strftime(
        "%d/%m/%Y %H:%M"
    )
    table["confidence"] = (table["confidence"].fillna(0) * 100).round().astype(int).astype(str) + "%"
    table.columns = [
        "Thời gian",
        "Hội thoại",
        "Turn",
        "Câu hỏi học viên",
        "Phân loại",
        "Chủ đề",
        "Tin cậy",
    ]
    st.dataframe(table, hide_index=True, width="stretch", height=620)


def render_alerts(turns: pd.DataFrame) -> None:
    st.markdown(
        '<div class="section-title"><h1>Alerts</h1>'
        "<p>Các tín hiệu cần giảng viên hoặc đội kỹ thuật xem lại.</p></div>",
        unsafe_allow_html=True,
    )
    alerts = turns.loc[turns["category"].isin(["Tutor Limitation", "Learning Difficulty"])]
    for _, row in alerts.head(30).iterrows():
        category = str(row["category"])
        with st.container(border=True):
            col1, col2 = st.columns([0.83, 0.17])
            with col1:
                st.markdown(
                    f"**{category} · {row['topic']}**  \n"
                    f"{row['reason']}  \n"
                    f"`{row['turn_id']}` · {_safe_text(row['student_content'], 210)}"
                )
            with col2:
                st.caption(row["message_created_at"].strftime("%d/%m · %H:%M"))
                st.button("Đã xem", key=f"ack-{row['turn_id']}", width="stretch")


def render_topics(turns: pd.DataFrame) -> None:
    st.markdown(
        '<div class="section-title"><h1>Topics</h1>'
        "<p>Khối lượng câu hỏi và friction theo từng chủ đề.</p></div>",
        unsafe_allow_html=True,
    )
    summary = (
        turns.groupby(["topic", "category"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=list(COLORS), fill_value=0)
    )
    summary["Tổng lượt"] = summary.sum(axis=1)
    summary = summary.sort_values("Tổng lượt", ascending=False).reset_index()
    st.dataframe(summary, hide_index=True, width="stretch", height=520)


def render_reports(turns: pd.DataFrame) -> None:
    st.markdown(
        '<div class="section-title"><h1>Reports</h1>'
        "<p>Xuất dữ liệu tổng hợp để dùng trong validation và demo.</p></div>",
        unsafe_allow_html=True,
    )
    conversations = conversation_view(turns)
    c1, c2, c3 = st.columns(3)
    c1.metric("Hội thoại", f"{len(conversations):,}")
    c2.metric("Lượt hỏi–đáp", f"{len(turns):,}")
    c3.metric(
        "Friction rate",
        f"{(conversations['category'].ne('Normal / No issue').mean() * 100):.1f}%"
        if len(conversations)
        else "0%",
    )
    export = turns.copy()
    export["message_created_at"] = export["message_created_at"].astype(str)
    st.download_button(
        "Tải báo cáo CSV",
        export.to_csv(index=False).encode("utf-8-sig"),
        "learning_analytics_report.csv",
        "text/csv",
        width="content",
    )


def render_settings(data_path: Path, pipeline_mode: str, data_source: str) -> None:
    st.markdown(
        '<div class="section-title"><h1>Settings</h1>'
        "<p>Cấu hình nguồn dữ liệu và contract tích hợp pipeline.</p></div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.text_input(
            "Nguồn dữ liệu",
            "Static demo (không đọc thư mục data/)"
            if data_source == "static"
            else str(data_path),
            disabled=True,
        )
        st.text_input("Pipeline hiện tại", pipeline_mode, disabled=True)
        st.code(
            """
# codebase/pipeline.py
def enrich_dashboard_turns(turns: pd.DataFrame) -> pd.DataFrame:
    # Required columns: turn_id, category
    # Optional: reason, confidence, topic
    return enriched_turns
            """.strip(),
            language="python",
        )
        st.caption(
            "Khi dữ liệu thật sẵn sàng, đặt FRONTEND_DATA_SOURCE=csv. "
            "Frontend tự phát hiện pipeline trên mà không cần sửa UI."
        )


def render_sidebar(pipeline_mode: str) -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="brand">
              <div class="brand-mark"><span></span><i></i><b></b></div>
              <div><strong>AI Learning</strong><small>Analytics Copilot</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        pages = [
            ("✦", "Live Dashboard"),
            ("◉", "Conversations"),
            ("▧", "Reports"),
            ("⚙", "Settings"),
        ]
        if "page" not in st.session_state:
            st.session_state.page = "Live Dashboard"
        for icon, label in pages:
            active = st.session_state.page == label
            if st.button(
                f"{icon}   {label}",
                key=f"nav-{label}",
                width="stretch",
                type="primary" if active else "secondary",
            ):
                st.session_state.page = label
                st.rerun()

        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="processing-card">
              <strong><i></i> Live Processing</strong>
              <p>Đang xử lý dữ liệu<br><span>{html.escape(pipeline_mode)}</span></p>
              <small>Sẵn sàng nhận batch mới</small>
            </div>
            <div class="profile">
              <div class="avatar">A</div>
              <div><strong>GV. Minh Anh</strong><small>Giảng viên</small></div>
              <span>⌄</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    return st.session_state.page


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --ink: #111528;
          --muted: #8F96AA;
          --border: #E8EBF3;
          --purple: #7557F6;
          --canvas: #F6F7FB;
          --mock-sidebar-width: 154px;
        }
        * { box-sizing: border-box; }
        html, body, .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMarkdownContainer"],
        [data-baseweb],
        button, input, textarea, select,
        svg text {
          font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
            "Segoe UI", sans-serif !important;
        }
        .stApp { background: var(--canvas); color: var(--ink); }
        #MainMenu, [data-testid="stHeader"], [data-testid="stToolbar"],
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {
          display: none !important;
        }
        [data-testid="stAppViewContainer"] > .main { background: var(--canvas); }
        .block-container {
          max-width: none;
          padding: 0 !important;
        }
        [data-testid="stVerticalBlock"] { gap: 0; }
        .stHtml { width: 100%; }
        .app-shell {
          width: 100%;
          min-height: 100vh;
          display: grid;
          grid-template-columns: var(--mock-sidebar-width, 144px) minmax(0, 1fr);
          background: var(--canvas);
          color: var(--ink);
        }
        .dashboard-main {
          min-width: 0;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          padding: 15px 17px 10px;
        }
        .dashboard-header {
          min-height: 46px;
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
        }
        .page-title { padding: 0; }
        .page-title h1 { margin: 0; font-size: 17px; letter-spacing: 0; line-height: 1.15; }
        .page-title h1 span {
          display: inline-block; vertical-align: 2px; margin-left: 6px; padding: 2px 5px;
          border-radius: 5px; font-size: 6.5px; letter-spacing: 0;
          color: #159C65; background: #DDF8EC;
        }
        .page-title p { margin: 7px 0 0; font-size: 7.7px; color: #959BAD; }
        .header-actions {
          display: flex;
          align-items: center;
          gap: 11px;
          padding-top: 1px;
          color: #777E94;
          font-size: 7.2px;
        }
        .clock:before {
          content: "";
          display: inline-block;
          width: 7px;
          height: 7px;
          margin-right: 5px;
          vertical-align: -1px;
          border-radius: 50%;
          border: 1px solid #A6AEC0;
        }
        .time-select {
          width: 128px;
          height: 27px;
          display: inline-flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 10px;
          border: 1px solid #E5E7EF;
          border-radius: 6px;
          background: #FFFFFF;
          color: #4C5265;
          font-size: 7.5px;
        }
        .time-select b { font-size: 10px; line-height: 1; }
        .notification {
          position: relative;
          width: 21px;
          height: 21px;
          display: inline-grid;
          place-items: center;
          color: #5F687D;
        }
        .notification-icon {
          display: block;
          width: 14px;
          height: 14px;
        }
        .notification i {
          position: absolute;
          right: 2px;
          top: 2px;
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #FA486A;
          box-shadow: 0 0 0 2px #FFFFFF;
        }
        .metric-grid {
          display: grid; grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 11px; margin: 4px 0 10px;
        }
        .metric-card, .panel {
          background: #FFFFFF; border: 1px solid var(--border); border-radius: 8px;
          box-shadow: 0 1px 2px rgba(18, 26, 48, .015);
        }
        .metric-card { min-width: 0; height: 113px; padding: 13px 12px 8px; overflow: hidden; }
        .metric-head {
          display: flex; align-items: center; gap: 7px; min-height: 20px;
          font-size: 8.2px; color: #4C5265; font-weight: 750; white-space: nowrap;
        }
        .metric-icon {
          display: grid; place-items: center; width: 20px; height: 20px;
          border-radius: 50%; font-size: 8px; font-weight: 900;
        }
        .metric-value { margin-top: 6px; font-size: 22px; line-height: 1; font-weight: 800; }
        .metric-sub { margin-top: 6px; color: #8C92A5; font-size: 7.3px; }
        .spark { width: 100%; height: 24px; margin-top: 8px; }
        .spark svg { width: 100%; height: 100%; overflow: visible; }
        .dashboard-grid { display: grid; gap: 10px; margin-bottom: 10px; }
        .dashboard-grid-top {
          grid-template-columns: minmax(0, 1.6fr) minmax(170px, .78fr) minmax(210px, .95fr);
          grid-template-rows: 205px 45px;
        }
        .dashboard-grid-bottom { grid-template-columns: minmax(0, 1.73fr) minmax(285px, .95fr); }
        .trend-panel, .issues-panel { height: 205px; }
        .alerts-panel {
          grid-column: 3;
          grid-row: 1 / span 2;
          height: auto;
        }
        .conversations-panel, .topic-panel { height: 169px; }
        .panel { min-width: 0; padding: 12px; overflow: hidden; }
        .panel-heading {
          min-height: 25px; display: flex; align-items: flex-start;
          justify-content: space-between; gap: 9px; margin-bottom: 7px;
        }
        .panel-heading h3 { margin: 0; font-size: 9.2px; font-weight: 800; color: #2E3344; }
        .ghost-button {
          appearance: none; border: 0; background: transparent; color: #9298A9;
          font: inherit; font-size: 7px; white-space: nowrap; padding: 1px 0;
        }
        .legend { display: flex; gap: 14px; margin-top: 9px; }
        .legend span { display: inline-flex; align-items: center; font-size: 7px; color: #858B9E; }
        .legend i { width: 5px; height: 5px; border-radius: 50%; margin-right: 5px; }
        .trend-svg { display: block; width: 100%; height: 145px; object-fit: fill; border: 0; }
        .issue-list { padding: 2px 0 1px; }
        .issue-row {
          display: grid; grid-template-columns: 13px minmax(56px, 1fr) minmax(42px, .62fr) 35px;
          align-items: center; gap: 6px; padding: 6px 0; font-size: 7.3px;
        }
        .rank { color: #9095A7; font-weight: 700; }
        .issue-name { color: #4A4F61; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .issue-bar { display: block; height: 3px; border-radius: 5px; background: #EEEAFD; overflow: hidden; }
        .issue-bar i { display: block; height: 100%; background: #7656F5; border-radius: inherit; }
        .issue-count { color: #969BAD; text-align: right; font-size: 6.7px; }
        .alerts-panel { padding-bottom: 6px; }
        .alert-row {
          display: grid; grid-template-columns: 6px minmax(0, 1fr) 30px; gap: 7px;
          align-items: start; padding: 6px 0; border-top: 1px solid #F0F1F5;
        }
        .alert-row:first-child { border-top: 0; }
        .alert-dot { width: 5px; height: 5px; border-radius: 50%; margin-top: 4px; }
        .alert-row strong { display: block; font-size: 7.2px; color: #42485B; }
        .alert-row p { margin: 2px 0; font-size: 6.7px; color: #858B9D; line-height: 1.32; }
        .alert-row a { font-size: 6.5px; color: #6F54E8; }
        .alert-row time { font-size: 6.5px; color: #A1A6B6; text-align: right; }
        .action-card {
          grid-column: 1 / span 2;
          grid-row: 2;
          min-width: 0;
          height: 45px;
          display: grid;
          grid-template-columns: 24px minmax(0, 1fr) auto;
          align-items: center;
          gap: 10px;
          padding: 8px 10px;
          border: 1px solid #FFE3C6;
          border-radius: 8px;
          background: #FFF8EF;
        }
        .action-icon {
          width: 22px;
          height: 22px;
          display: grid;
          place-items: center;
          border-radius: 50%;
          background: #FFE9D7;
          color: #FF8A3D;
          font-size: 11px;
          font-weight: 900;
        }
        .action-copy { min-width: 0; }
        .action-copy strong {
          display: block;
          color: #4D5367;
          font-size: 7.7px;
          font-weight: 800;
        }
        .action-copy p {
          margin: 2px 0 0;
          color: #7A8094;
          font-size: 7px;
          line-height: 1.28;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .action-button {
          height: 24px;
          padding: 0 10px;
          border: 0;
          border-radius: 6px;
          background: #8B6CFF;
          color: #FFFFFF;
          font: inherit;
          font-size: 7px;
          font-weight: 800;
          white-space: nowrap;
        }
        .conversation-row {
          display: grid; grid-template-columns: 45px minmax(0, 1fr) 88px;
          gap: 8px; align-items: center; min-height: 25px; padding: 4px 0;
          border-top: 1px solid #EFF0F4;
        }
        .conversation-row:first-child { border-top: 0; }
        .time-badge {
          display: inline-flex; align-items: center; color: #7760E9; font-size: 7px;
        }
        .time-badge:before {
          content: ""; width: 4px; height: 4px; margin-right: 5px; border-radius: 50%;
          background: #8A6BFF; box-shadow: 0 0 0 3px #8A6BFF12;
        }
        .conversation-copy { min-width: 0; }
        .conversation-copy p {
          margin: 0 0 3px; color: #525769; font-size: 7.1px; overflow: hidden;
          text-overflow: ellipsis; white-space: nowrap;
        }
        .conversation-copy span {
          display: inline-block; padding: 2px 5px; border-radius: 4px; font-size: 6.2px;
        }
        .topic-pill {
          justify-self: end; max-width: 88px; padding: 3px 5px; border-radius: 4px;
          color: #777D8F; background: #F4F5F8; font-size: 6.2px; white-space: nowrap;
          overflow: hidden; text-overflow: ellipsis;
        }
        .topic-map {
          display: grid; grid-template-columns: repeat(6, minmax(0, 1fr));
          grid-auto-rows: 38px; gap: 6px;
        }
        .topic-block {
          position: relative; min-width: 0; padding: 7px 8px; border-radius: 6px;
          display: flex; flex-direction: column; justify-content: center;
        }
        .topic-block strong { font-size: 14px; line-height: 1; }
        .topic-block span {
          max-width: 82%; margin-top: 4px; font-size: 6.4px;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .topic-block small { position: absolute; top: 7px; right: 7px; font-size: 5.9px; opacity: .7; }
        .topic-1, .topic-2 { grid-column: span 3; }
        .topic-3, .topic-4, .topic-5 { grid-column: span 2; }
        .topic-6, .topic-7 { grid-column: span 3; }
        .status-bar {
          display: flex; align-items: center; justify-content: space-between; gap: 12px;
          margin-top: auto;
          min-height: 27px; padding: 0 10px; border: 1px solid var(--border);
          border-radius: 7px; background: white; color: #8D93A5; font-size: 7px;
        }
        .empty-note { padding: 14px 0; color: #9AA0B2; font-size: 7.2px; text-align: center; }
        .section-title h1 { margin: 4px 0 3px; font-size: 24px; }
        .section-title p { margin: 0 0 20px; color: #8C92A4; font-size: 12px; }
        [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
        [data-testid="stMetric"] {
          padding: 16px; background: white; border: 1px solid var(--border); border-radius: 10px;
        }
        @media (min-width: 1350px) {
          :root { --mock-sidebar-width: 165px; }
          .dashboard-main { padding: 22px 28px 14px; }
          .app-shell { grid-template-columns: var(--mock-sidebar-width, 154px) minmax(0, 1fr); }
          .metric-card { height: 126px; }
          .dashboard-grid-top { grid-template-rows: 234px 53px; }
          .trend-panel, .issues-panel { height: 234px; }
          .action-card { height: 53px; }
          .conversations-panel, .topic-panel { height: 194px; }
          .trend-svg { height: 171px; }
          .topic-map { grid-auto-rows: 45px; }
          .metric-value { font-size: 27px; }
          .page-title h1 { font-size: 22px; }
        }
        @media (max-width: 960px) {
          :root { --mock-sidebar-width: 140px; }
          .app-shell { grid-template-columns: var(--mock-sidebar-width, 122px) minmax(0, 1fr); }
          .dashboard-main { padding: 12px; }
          .metric-grid { grid-template-columns: repeat(2, 1fr); }
          .dashboard-grid-top, .dashboard-grid-bottom {
            grid-template-columns: 1fr;
            grid-template-rows: auto;
          }
          .trend-panel, .issues-panel, .alerts-panel,
          .conversations-panel, .topic-panel { height: auto; }
          .alerts-panel, .action-card {
            grid-column: auto;
            grid-row: auto;
          }
          .conversation-row { grid-template-columns: 42px minmax(0, 1fr); }
          .topic-pill { display: none; }
          .status-bar { align-items: flex-start; flex-direction: column; padding: 9px; }
        }
        /* Larger shared typography for readability across the three pages. */
        .page-title h1 { font-size: 20px; }
        .page-title h1 span,
        .alert-row a,
        .alert-row time,
        .conversation-copy span,
        .topic-pill,
        .topic-block small { font-size: 10.5px; }
        .page-title p,
        .time-select,
        .metric-sub,
        .ghost-button,
        .legend span,
        .issue-count,
        .alert-row p,
        .action-copy p,
        .action-button,
        .time-badge,
        .conversation-copy p,
        .topic-block span,
        .status-bar,
        .empty-note { font-size: 11.5px; }
        .header-actions,
        .issue-row,
        .alert-row strong { font-size: 12px; }
        .metric-head,
        .action-copy strong { font-size: 12.5px; }
        .panel-heading h3 { font-size: 13px; }
        .time-select b { font-size: 13px; }
        .metric-icon { font-size: 12px; }
        .action-icon { font-size: 14px; }
        .topic-block strong { font-size: 16px; }
        .metric-value { font-size: 25px; }
        .section-title h1 { font-size: 27px; }
        .section-title p { font-size: 14px; }
        @media (min-width: 1350px) {
          .page-title h1 { font-size: 26px; }
          .metric-value { font-size: 30px; }
          .metric-card { height: 138px; }
          .dashboard-grid-top { grid-template-rows: 270px 68px; }
          .trend-panel, .issues-panel { height: 270px; }
          .action-card { height: 68px; }
          .conversations-panel, .topic-panel { height: 225px; }
          .trend-svg { height: 198px; }
          .topic-map { grid-auto-rows: 51px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<style>" + taskbar_css("sticky") + "</style>", unsafe_allow_html=True)


def render() -> None:
    inject_styles()

    data_source = os.getenv("FRONTEND_DATA_SOURCE", "static").strip().lower()
    data_path = Path(os.getenv("DATA_PATH", str(DEFAULT_DATA_PATH)))
    if data_source == "static":
        pipeline = PipelineResult(turns=build_static_turns(), mode="Static demo")
    else:
        if not data_path.exists():
            st.error(
                "Không tìm thấy dữ liệu CSV. Hãy đặt DATA_PATH hoặc chuyển "
                "FRONTEND_DATA_SOURCE=static."
            )
            st.stop()
        turns = load_turns(str(data_path), data_path.stat().st_mtime)
        pipeline = apply_pipeline_adapter(turns)
    render_dashboard(pipeline.turns, pipeline.mode)


def main() -> None:
    st.set_page_config(
        page_title="AI Learning Analytics Copilot",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    page = get_active_page(default="dashboard")
    if page == "conversations":
        import conversations as conversations_page

        conversations_page.render()
    else:
        render()


if __name__ == "__main__":
    main()
