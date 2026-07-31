"""AI Learning Analytics Copilot — 1 web Streamlit, chạy local bằng 1 lệnh:

    streamlit run app.py

4 trang (điều hướng sidebar):
  📡 Live Dashboard — tổng quan tuần/ngày: KPI, friction theo ngày, top vấn đề, khuyến nghị
  💬 Conversations  — danh sách hội thoại theo tuần/ngày, đọc nguyên văn + panel phân tích
  📑 Reports        — tổng hợp theo tuần, so sánh tuần trước, heatmap chủ đề × ngày, xuất báo cáo
  🎓 Chat AI Tutor  — học viên hỏi đáp trên bài giảng hoặc file tự upload (sinh hội thoại demo)

Dữ liệu gom theo TUẦN — không giới hạn số buổi; data thêm ngày/tuần mới sẽ tự xuất hiện.
Logic dùng chung nằm ở ui_common.py; từng trang là script trong app_pages/.
"""
import streamlit as st

st.set_page_config(page_title="AI Learning Analytics Copilot", page_icon="🎓", layout="wide")

with st.sidebar:
    st.markdown("**🎓 AI Learning**")
    st.caption("Analytics Copilot")

page = st.navigation([
    st.Page("app_pages/live_dashboard.py", title="Live Dashboard", icon=":material/monitoring:", default=True),
    st.Page("app_pages/conversations.py", title="Conversations", icon=":material/forum:"),
    st.Page("app_pages/reports.py", title="Reports", icon=":material/lab_profile:"),
    st.Page("app_pages/chat_tutor.py", title="Chat AI Tutor", icon=":material/school:"),
])
page.run()
