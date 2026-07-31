from __future__ import annotations

from textwrap import dedent
from urllib.parse import quote

import streamlit as st


PURPLE = "#7048E8"
ORANGE = "#FF922B"
RED = "#F04F5F"
BLUE = "#4299E1"
GREEN = "#38B87C"


def _sparkline(color: str, points: str) -> str:
    gradient_id = f"fade-{color[1:]}"
    return f"""
    <svg class="report-sparkline" viewBox="0 0 180 38" preserveAspectRatio="none" role="img" aria-label="Xu hướng chỉ số">
      <defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="{color}" stop-opacity=".22"/><stop offset="100%" stop-color="{color}" stop-opacity=".02"/>
      </linearGradient></defs>
      <path d="{points} L180 38 L0 38 Z" fill="url(#{gradient_id})"/>
      <path d="{points}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>"""


def _metric_card(label: str, value: str, delta: str, color: str, icon: str, points: str) -> str:
    value_color = "#131726" if label == "Tổng cuộc hội thoại" else color
    return f"""
    <article class="report-metric">
      <div class="report-metric-title"><span class="metric-symbol" style="color:{color};background:{color}16">{icon}</span><strong>{label}</strong></div>
      <div class="report-metric-value" style="color:{value_color}">{value}</div>
      <div class="metric-change"><b>{delta}</b><span>so với 7 ngày trước</span></div>
      {_sparkline(color, points)}
    </article>"""


def _stacked_chart() -> str:
    days = [
        ("22/05", (35, 23, 17, 25)), ("23/05", (34, 24, 17, 25)),
        ("24/05", (35, 23, 17, 25)), ("25/05", (34, 24, 17, 25)),
        ("26/05", (34, 24, 17, 25)), ("27/05", (35, 23, 18, 24)),
        ("28/05", (34, 24, 17, 25)),
    ]
    bars = []
    for label, values in days:
        segments = "".join(
            f'<i style="height:{value}%;background:{color}"></i>'
            for value, color in zip(values, (PURPLE, ORANGE, BLUE, GREEN))
        )
        bars.append(f'<div class="stack-column"><div class="stack-bar">{segments}</div><span>{label}</span></div>')
    return "".join(bars)


def _top_issues() -> str:
    issues = (
        ("Context Window", 112, "13.8%", 100), ("RAG Retrieval", 98, "11.9%", 87),
        ("Agent Memory", 76, "9.2%", 68), ("Prompt Engineering", 70, "8.5%", 62),
        ("Function Calling", 64, "7.6%", 57),
    )
    return "".join(
        f'<div class="ranked-issue"><span>{index}</span><strong>{name}</strong>'
        f'<i><b style="width:{width}%"></b></i><small>{count} ({percent})</small></div>'
        for index, (name, count, percent, width) in enumerate(issues, 1)
    )


def _trend_analysis() -> str:
    rows = (
        ("↓", PURPLE, "Learning Difficulty<br>giảm", "Học viên hiểu bài tốt hơn ở các topic: Tool Usage, Function Calling."),
        ("↗", GREEN, "Context Window vẫn là vấn đề lớn nhất", "Cần bổ sung ví dụ và bài tập thực hành."),
        ("↑", ORANGE, "Tutor Limitation giảm 2%", "AI Tutor đã tìm được nhiều tài liệu phù hợp hơn."),
        ("↓", BLUE, "Off-topic giảm nhẹ 1%", "Học viên tập trung hơn vào nội dung bài học."),
    )
    return "".join(
        f'<div class="analysis-row"><span style="color:{color};background:{color}16">{icon}</span>'
        f'<div><strong style="color:{color}">{title}</strong><p>{copy}</p></div></div>'
        for icon, color, title, copy in rows
    )


def _heatmap() -> str:
    rows = (
        ("Context Window", (78, 82, 85, 87, 80, 83, 84), "83%"),
        ("RAG Retrieval", (65, 68, 70, 73, 69, 71, 74), "70%"),
        ("Agent Memory", (45, 48, 52, 50, 47, 48, 51), "49%"),
        ("Prompt Engineering", (38, 35, 40, 42, 36, 39, 41), "39%"),
        ("Tool Usage", (30, 28, 32, 33, 29, 31, 34), "31%"),
        ("Function Calling", (25, 22, 24, 26, 23, 26, 27), "24%"),
    )
    def cell(value: int) -> str:
        if value >= 75: background, foreground = "#7048E8", "#FFFFFF"
        elif value >= 60: background, foreground = "#9A7CF0", "#FFFFFF"
        elif value >= 45: background, foreground = "#B8A4F3", "#3F355C"
        elif value >= 30: background, foreground = "#D6CBF7", "#4D4760"
        else: background, foreground = "#EEE9FC", "#555064"
        return f'<span class="heat-cell" style="background:{background};color:{foreground}">{value}%</span>'
    body = []
    for topic, values, average in rows:
        body.append(f'<strong class="heat-topic">{topic}</strong>' + "".join(cell(value) for value in values) + f'<b class="heat-average">{average}</b>')
    return "".join(body)


def _statistics() -> str:
    items = (
        ("Thời lượng trung bình<br>mỗi hội thoại", "8m 24s", "↑ 12%", "up"),
        ("Số học viên tương tác", "312", "↑ 15%", "up"),
        ("Số hội thoại / học viên", "8.1", "↓ 5%", "down"),
        ("Tỉ lệ hài lòng của học viên", "4.3 / 5", "↑ 6%", "up"),
        ("Số cảnh báo được tạo", "48", "↑ 20%", "up"),
        ("Thời gian phản hồi TB của AI", "6.2s", "↓ 8%", "up"),
    )
    return "".join(
        f'<div class="stat-item"><span>{label}</span><strong>{value}</strong><b class="{tone}">{delta}</b></div>'
        for label, value, delta, tone in items
    )

def _report_html() -> str:
    metric_specs = (
        ("Tổng cuộc hội thoại", "2,540", "↑ 18%", PURPLE, "◉", "M0 31 L9 19 L18 24 L27 34 L36 27 L45 18 L54 30 L63 27 L72 35 L81 25 L90 29 L99 23 L108 31 L117 29 L126 34 L135 27 L144 31 L153 23 L162 28 L171 20 L180 19"),
        ("Learning Difficulty", "32%", "↓ 5%", ORANGE, "▦", "M0 31 L9 18 L18 27 L27 34 L36 25 L45 18 L54 31 L63 34 L72 27 L81 23 L90 31 L99 35 L108 27 L117 25 L126 29 L135 27 L144 21 L153 24 L162 19 L171 20 L180 18"),
        ("Tutor Limitation", "12%", "↓ 2%", RED, "▦", "M0 29 L9 22 L18 25 L27 31 L36 27 L45 30 L54 33 L63 31 L72 34 L81 30 L90 27 L99 31 L108 33 L117 32 L126 27 L135 25 L144 15 L153 20 L162 18 L171 23 L180 21"),
        ("Off-topic / Intent Drift", "6%", "↓ 1%", BLUE, "➤", "M0 32 L9 26 L18 25 L27 29 L36 31 L45 27 L54 30 L63 25 L72 22 L81 29 L90 29 L99 23 L108 20 L117 25 L126 27 L135 18 L144 23 L153 18 L162 22 L171 20 L180 21"),
        ("Normal / No Issue", "50%", "↑ 8%", GREEN, "✓", "M0 31 L9 28 L18 17 L27 24 L36 20 L45 12 L54 17 L63 14 L72 20 L81 12 L90 14 L99 18 L108 25 L117 29 L126 26 L135 31 L144 29 L153 27 L162 30 L171 26 L180 27"),
    )
    metrics = "".join(_metric_card(*spec) for spec in metric_specs)
    csv_data = quote(
        "metric,value,change\nTotal conversations,2540,18%\nLearning Difficulty,32%,-5%\n"
        "Tutor Limitation,12%,-2%\nOff-topic / Intent Drift,6%,-1%\nNormal / No Issue,50%,8%\n"
    )
    return dedent(f"""
    <section class="report-shell" aria-label="Reports - AI Learning Analytics Copilot">
      <main class="report-main">
        <header class="report-header">
          <div class="report-title"><h1>Reports <span title="Thông tin báo cáo">i</span></h1><p>Tổng hợp và phân tích hiệu quả học tập</p></div>
          <a class="export-report" href="data:text/csv;charset=utf-8,{csv_data}" download="ai-learning-report-22-28-05-2025.csv">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v11m0 0 4-4m-4 4-4-4M5 17v3h14v-3"/></svg>Xuất báo cáo
          </a>
        </header>

        <section class="report-filters" aria-label="Bộ lọc thời gian">
          <div class="date-range"><svg viewBox="0 0 24 24"><rect x="3.5" y="5.5" width="17" height="15" rx="2"/><path d="M7 3v5M17 3v5M3.5 10h17"/></svg><strong>22/05/2025 - 28/05/2025</strong><span>⌄</span></div>
          <div class="range-tabs"><button class="active">7 ngày qua</button><button>30 ngày qua</button><button>Tùy chỉnh</button></div>
        </section>

        <section class="report-metrics">{metrics}</section>

        <section class="report-middle">
          <article class="report-panel time-trend-panel">
            <div class="report-panel-heading"><h2>Xu hướng theo thời gian <i>i</i></h2><a href="#report-details">Xem chi tiết →</a></div>
            <div class="chart-legend"><span><i style="background:{PURPLE}"></i>Learning Difficulty</span><span><i style="background:{ORANGE}"></i>Tutor Limitation</span><span><i style="background:{BLUE}"></i>Off-topic / Drift</span><span><i style="background:{GREEN}"></i>Normal</span></div>
            <div class="stacked-chart"><div class="axis-labels"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div><div class="chart-grid"><i></i><i></i><i></i><i></i><i></i><div class="stack-columns">{_stacked_chart()}</div></div></div>
          </article>

          <article class="report-panel top-issues-panel">
            <div class="report-panel-heading"><h2>Top vấn đề (7 ngày qua)</h2><a href="#report-details">Xem chi tiết →</a></div>
            <div class="ranked-list">{_top_issues()}</div>
            <a class="all-issues" href="?page=conversations" target="_self">Xem tất cả vấn đề</a>
          </article>

          <article class="report-panel trend-analysis-panel">
            <div class="report-panel-heading"><h2>Phân tích xu hướng</h2><a href="#report-details">Xem chi tiết →</a></div>
            <div class="analysis-list">{_trend_analysis()}</div>
          </article>
        </section>

        <section class="report-lower" id="report-details">
          <div class="report-lower-left">
            <article class="report-panel heatmap-panel">
              <div class="report-panel-heading"><h2>Heatmap theo chủ đề <i>i</i></h2><a href="#report-details">Xem chi tiết →</a></div>
              <div class="heatmap-grid"><strong class="heat-header-topic">Chủ đề</strong><span>22/05</span><span>23/05</span><span>24/05</span><span>25/05</span><span>26/05</span><span>27/05</span><span>28/05</span><b>TB tuần</b>{_heatmap()}</div>
              <div class="heat-legend"><span><i style="background:#EEE9FC"></i>0-25% (Thấp)</span><span><i style="background:#D6CBF7"></i>25-50% (Trung bình)</span><span><i style="background:#B8A4F3"></i>50-75% (Cao)</span><span><i style="background:#7048E8"></i>75-100% (Rất cao)</span></div>
            </article>

            <div class="report-notes-grid">
              <article class="report-panel note-panel"><div class="report-panel-heading"><h2>Nhận định tổng quan <i>i</i></h2></div><ul class="insight-list"><li>Học viên vẫn gặp khó khăn chủ yếu ở topic “Context Window” và “RAG Retrieval”.</li><li>Xu hướng Learning Difficulty giảm nhẹ, cho thấy bài giảng đang phát huy hiệu quả.</li><li>Cần tăng cường bài tập thực hành về Context Window và Memory.</li></ul></article>
              <article class="report-panel note-panel"><div class="report-panel-heading"><h2>Gợi ý cải thiện <i>i</i></h2></div><ul class="recommendation-list"><li><span>◈</span>Bổ sung slide so sánh Context vs Memory</li><li><span>▣</span>Thêm ví dụ thực tế về giới hạn Context Window</li><li><span>◫</span>Tạo bài tập thực hành với truy xuất (RAG)</li><li><span>◎</span>Tổng hợp FAQ cho AI Tutor</li></ul></article>
            </div>
          </div>

          <div class="report-lower-right">
            <article class="report-panel distribution-panel">
              <div class="report-panel-heading"><h2>Phân bổ mức độ <i>i</i></h2><a href="#report-details">Xem chi tiết →</a></div>
              <div class="distribution-content"><div class="donut"><div><span>Tổng</span><strong>2,540</strong><small>hội thoại</small></div></div><div class="distribution-legend"><div><i style="background:{PURPLE}"></i><strong>Learning Difficulty</strong><span>812 (32%)</span></div><div><i style="background:{ORANGE}"></i><strong>Tutor Limitation</strong><span>305 (12%)</span></div><div><i style="background:{BLUE}"></i><strong>Off-topic / Drift</strong><span>152 (6%)</span></div><div><i style="background:{GREEN}"></i><strong>Normal / No Issue</strong><span>1,271 (50%)</span></div></div></div>
            </article>

            <article class="report-panel statistics-panel"><div class="report-panel-heading"><h2>Thống kê tổng quan <i>i</i></h2></div><div class="statistics-grid">{_statistics()}</div></article>
          </div>
        </section>

        <div class="report-status"><span><i></i>Báo cáo được cập nhật lần cuối: 10:32 AM - 28/05/2025</span><span>Dữ liệu được phân tích bởi AI. Sai số có thể xảy ra. <b>✓</b></span></div>
      </main>
    </section>
    """).replace("\n", "").strip()

def inject_styles() -> None:
    st.markdown("""
    <style>
    :root{--ink:#111528;--muted:#8F96AA;--border:#E8EBF3;--purple:#7048E8;--canvas:#F6F7FB;--mock-sidebar-width:144px}
    *{box-sizing:border-box}html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMarkdownContainer"],[data-baseweb],button,input,textarea,select,svg text{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important}
    html{scroll-behavior:smooth}body,.stApp{margin:0;background:var(--canvas);color:var(--ink)}
    #MainMenu,footer,[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important}
    [data-testid="stAppViewContainer"]>.main{background:var(--canvas)}.block-container{max-width:none;padding:0!important}[data-testid="stVerticalBlock"]{gap:0}.stHtml{width:100%}
    .report-shell{width:100%;min-height:100vh;display:grid;grid-template-columns:var(--mock-sidebar-width) minmax(0,1fr);background:var(--canvas);color:var(--ink)}
    .report-main{grid-column:2;min-width:0;min-height:100vh;padding:15px 17px 12px}.report-header{min-height:49px;display:flex;justify-content:space-between;align-items:flex-start;gap:18px}
    .report-title h1{display:flex;align-items:center;gap:7px;margin:0;color:#111528;font-size:17px;line-height:1.15;font-weight:800;letter-spacing:-.01em}
    .report-title h1 span,.report-panel-heading h2 i{width:12px;height:12px;display:inline-grid;place-items:center;border:1px solid #ABB1C0;border-radius:50%;color:#9299A9;font-size:7px;font-style:normal;font-weight:750}
    .report-title p{margin:6px 0 0;color:#949BAD;font-size:7.7px;line-height:1.2}
    .export-report{height:29px;display:inline-flex;align-items:center;gap:7px;padding:0 12px;border:1px solid #E1E4EC;border-radius:6px;background:#fff;color:#5C38D0!important;text-decoration:none!important;font-size:7.7px;font-weight:800;box-shadow:0 1px 2px rgba(18,26,48,.025)}
    .export-report svg{width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
    .report-filters{min-height:36px;display:flex;align-items:center;gap:10px;margin-bottom:9px}.date-range{height:30px;min-width:185px;display:inline-flex;align-items:center;gap:7px;padding:0 9px;border:1px solid #E4E7EF;border-radius:6px;background:#fff;color:#4E5467;font-size:7.7px}
    .date-range svg{width:12px;height:12px;fill:none;stroke:#72798D;stroke-width:1.7;stroke-linecap:round}.date-range strong{font-weight:650}.date-range span{margin-left:auto;color:#9298A9;font-size:9px}
    .range-tabs{display:flex;align-items:center;gap:5px}.range-tabs button{height:30px;min-width:68px;padding:0 12px;border:1px solid #E8EAF1;border-radius:5px;background:#fff;color:#5F6577;font-size:7.7px;font-weight:650}
    .range-tabs button.active{border-color:#DCD3FF;background:#EEE9FF;color:#5D3BD0;font-weight:800;box-shadow:inset 0 -2px 0 #8A6CF0}
    .report-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:10px}.report-metric,.report-panel{min-width:0;border:1px solid var(--border);border-radius:8px;background:#fff;box-shadow:0 1px 2px rgba(18,26,48,.015)}
    .report-metric{height:125px;padding:12px 12px 7px;overflow:hidden}.report-metric-title{min-height:20px;display:flex;align-items:center;gap:7px;color:#3F4558;font-size:7.7px;white-space:nowrap}
    .report-metric-title strong{min-width:0;overflow:hidden;text-overflow:ellipsis;font-weight:750}.metric-symbol{width:20px;height:20px;flex:0 0 20px;display:grid;place-items:center;border-radius:50%;font-size:9px;font-weight:900}
    .report-metric-value{margin:6px 0 5px;font-size:22px;line-height:1;font-weight:850;letter-spacing:-.02em}.metric-change{display:flex;align-items:center;gap:4px;min-height:12px;white-space:nowrap;font-size:6.8px}
    .metric-change b{color:#199561;font-size:7.2px;font-weight:800}.metric-change span{min-width:0;color:#767D90;overflow:hidden;text-overflow:ellipsis}.report-sparkline{display:block;width:100%;height:28px;margin-top:4px;overflow:hidden}
    .report-middle{display:grid;grid-template-columns:minmax(0,1.18fr) minmax(235px,.78fr) minmax(270px,.98fr);gap:10px;margin-bottom:10px}.report-panel{padding:12px;overflow:hidden}.report-middle>.report-panel{height:249px}
    .report-panel-heading{min-height:18px;display:flex;align-items:flex-start;justify-content:space-between;gap:9px;margin-bottom:9px}.report-panel-heading h2{display:flex;align-items:center;gap:6px;margin:0;color:#2C3142;font-size:9px;line-height:1.25;font-weight:800}
    .report-panel-heading h2 i{width:10px;height:10px;font-size:6px}.report-panel-heading>a{color:#7656E4!important;text-decoration:none!important;white-space:nowrap;font-size:6.8px}
    .chart-legend{display:flex;align-items:center;gap:14px;margin:1px 0 12px 14px;color:#666D80;font-size:6.7px}.chart-legend span{display:inline-flex;align-items:center;white-space:nowrap}.chart-legend i{width:6px;height:6px;margin-right:4px;border-radius:1px}
    .stacked-chart{height:174px;display:grid;grid-template-columns:25px minmax(0,1fr);gap:5px}.axis-labels{height:145px;display:flex;flex-direction:column;align-items:flex-end;justify-content:space-between;color:#81889B;font-size:6.5px}
    .chart-grid{position:relative;height:145px;border-bottom:1px solid #E8EAF0}.chart-grid>i{position:absolute;left:0;right:0;height:1px;background:#EFF1F5}.chart-grid>i:nth-child(1){top:0}.chart-grid>i:nth-child(2){top:25%}.chart-grid>i:nth-child(3){top:50%}.chart-grid>i:nth-child(4){top:75%}.chart-grid>i:nth-child(5){bottom:0}
    .stack-columns{position:absolute;inset:0 5px;display:flex;align-items:flex-end;justify-content:space-around;gap:8px}.stack-column{width:24px;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:flex-end}.stack-bar{width:18px;height:100%;display:flex;flex-direction:column-reverse;overflow:hidden;border-radius:2px 2px 0 0}.stack-bar i{width:100%;display:block}.stack-column>span{position:absolute;bottom:-20px;color:#686F82;font-size:6.5px}
    .ranked-list{padding-top:2px}.ranked-issue{display:grid;grid-template-columns:12px minmax(82px,1fr) minmax(50px,.8fr) 49px;align-items:center;gap:6px;min-height:30px;color:#565C6D;font-size:6.8px}.ranked-issue>span{color:#969BAD;font-weight:700}.ranked-issue strong{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:650}
    .ranked-issue>i{height:4px;display:block;overflow:hidden;border-radius:5px;background:#EEEAFB}.ranked-issue>i b{height:100%;display:block;border-radius:inherit;background:#7048E8}.ranked-issue small{color:#858B9D;font-size:6.3px;white-space:nowrap}.all-issues{height:29px;display:grid;place-items:center;margin-top:7px;border-radius:5px;background:#F5F2FF;color:#6442D3!important;text-decoration:none!important;font-size:7px;font-weight:800}
    .analysis-list{margin-top:-2px}.analysis-row{min-height:47px;display:grid;grid-template-columns:23px minmax(0,1fr);gap:8px;align-items:center;padding:6px 1px;border-top:1px solid #EFF0F4}.analysis-row:first-child{border-top:0}.analysis-row>span{width:22px;height:22px;display:grid;place-items:center;border-radius:50%;font-size:11px;font-weight:900}.analysis-row strong{display:block;font-size:7.2px;line-height:1.25;font-weight:800}.analysis-row p{margin:3px 0 0;color:#73798B;font-size:6.4px;line-height:1.3}    .report-lower{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(350px,.92fr);gap:10px}.report-lower-left,.report-lower-right{min-width:0;display:grid;gap:10px;align-content:start}.heatmap-panel{height:297px}
    .heatmap-grid{display:grid;grid-template-columns:minmax(82px,1.35fr) repeat(7,minmax(36px,1fr)) minmax(44px,.8fr);align-items:center;margin-top:4px;font-size:6.6px}.heatmap-grid>span,.heatmap-grid>b,.heat-header-topic{min-height:22px;display:grid;place-items:center;color:#575D70;font-weight:650}.heat-header-topic{justify-items:start}
    .heat-topic{height:27px;display:flex;align-items:center;padding-left:2px;color:#474D5E;white-space:nowrap;font-size:6.7px;font-weight:650}.heat-cell{height:27px;display:grid;place-items:center;border:1px solid #FFFFFF33;font-size:6.4px}.heat-average{height:27px;display:grid;place-items:center;color:#272C3A;background:#FAFAFC;font-size:6.8px}
    .heat-legend{display:flex;align-items:center;justify-content:space-around;gap:10px;margin-top:13px;color:#71778A;font-size:6.4px}.heat-legend span{display:inline-flex;align-items:center;white-space:nowrap}.heat-legend i{width:11px;height:11px;margin-right:5px;border-radius:2px}
    .report-notes-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.note-panel{height:133px}.note-panel .report-panel-heading{margin-bottom:6px}.insight-list,.recommendation-list{margin:0;padding:0 0 0 14px;color:#515769;font-size:6.6px;line-height:1.45}.insight-list li{margin-bottom:6px;padding-left:1px}.recommendation-list{list-style:none;padding-left:0}.recommendation-list li{display:grid;grid-template-columns:14px minmax(0,1fr);gap:3px;align-items:start;margin-bottom:5px}.recommendation-list span{color:#7656E4;font-weight:900}
    .distribution-panel{height:190px}.distribution-content{height:134px;display:grid;grid-template-columns:145px minmax(0,1fr);gap:12px;align-items:center}.donut{width:114px;height:114px;display:grid;place-items:center;justify-self:center;border-radius:50%;background:conic-gradient(#7048E8 0 32%,#FF922B 32% 44%,#4299E1 44% 50%,#38B87C 50% 100%);position:relative}.donut:before{content:"";position:absolute;inset:21px;border-radius:50%;background:#fff}.donut>div{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;line-height:1.15}.donut span,.donut small{color:#777D90;font-size:6.5px}.donut strong{margin:2px 0;color:#171B29;font-size:15px}
    .distribution-legend{display:grid;gap:12px}.distribution-legend>div{display:grid;grid-template-columns:7px minmax(90px,1fr) auto;align-items:center;gap:6px;color:#4E5465;font-size:7px}.distribution-legend i{width:7px;height:7px;border-radius:2px}.distribution-legend strong{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:650}.distribution-legend span{color:#686F81;white-space:nowrap}
    .statistics-panel{height:250px}.statistics-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));row-gap:24px;column-gap:14px;padding:14px 4px 2px}.stat-item{min-width:0}.stat-item>span{min-height:25px;display:block;color:#7A8193;font-size:6.5px;line-height:1.45}.stat-item strong{display:block;margin:5px 0 2px;color:#1A1E2C;font-size:15px;line-height:1;font-weight:800}.stat-item b{font-size:7px;font-weight:800}.stat-item b.up{color:#15945E}.stat-item b.down{color:#D84C5C}
    .report-status{min-height:30px;display:flex;align-items:center;justify-content:space-between;gap:15px;margin-top:10px;padding:0 11px;border:1px solid var(--border);border-radius:7px;background:#fff;color:#8A91A3;font-size:6.7px}.report-status span{display:inline-flex;align-items:center}.report-status i{width:7px;height:7px;margin-right:6px;border:2px solid #48B99B;border-radius:50%}.report-status b{margin-left:6px;color:#9FA5B4}
    @media(min-width:1350px){:root{--mock-sidebar-width:154px}.report-main{padding:22px 28px 14px}.report-title h1{font-size:22px}.report-title p{font-size:8px}.report-metric{height:138px;padding:14px 14px 8px}.report-metric-value{font-size:27px}.report-middle>.report-panel{height:272px}.stacked-chart,.chart-grid,.axis-labels{height:165px}.heatmap-panel{height:313px}.heat-topic,.heat-cell,.heat-average{height:30px}.note-panel{height:140px}.distribution-panel{height:200px}.statistics-panel{height:253px}}
    @media(max-width:1120px){.report-middle{grid-template-columns:1.25fr 1fr}.trend-analysis-panel{grid-column:1/-1;height:auto!important}.analysis-list{display:grid;grid-template-columns:1fr 1fr}.analysis-row:nth-child(2){border-top:0}.report-lower{grid-template-columns:1fr}.report-lower-right{grid-template-columns:.8fr 1.2fr}.distribution-panel,.statistics-panel{height:240px}}
    @media(max-width:820px){:root{--mock-sidebar-width:122px}.report-main{padding:12px}.report-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.report-middle{grid-template-columns:1fr}.report-middle>.report-panel{height:auto;min-height:250px}.trend-analysis-panel{grid-column:auto}.report-lower-right,.report-notes-grid{grid-template-columns:1fr}.distribution-panel,.statistics-panel{height:auto;min-height:220px}.heatmap-panel{overflow-x:auto}.heatmap-grid{min-width:590px}.report-status{flex-direction:column;align-items:flex-start;padding:8px 10px}}
    </style>
    """, unsafe_allow_html=True)
def render() -> None:
    inject_styles()
    st.html(_report_html())


if __name__ == "__main__":
    st.set_page_config(
        page_title="Reports · AI Learning Analytics Copilot",
        page_icon="▧",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render()