from collections import Counter

from friction_pipeline.labels import seed_label, topic_for
from friction_pipeline.phobert import PhoBERTTextClassifier
from friction_pipeline.text import normalize, split_prompt, typed_question


def test_normalizes_vietnamese_and_selected_text():
    assert normalize("Chưa hiểu Agent!") == "chua hieu agent"
    assert typed_question('(Trang 3, đoạn được chọn: "Tool")\nagent là gì') == "agent là gì"
    assert split_prompt('(Trang 3, đoạn được chọn: "Tool")\nagent là gì') == ("agent là gì", "Tool")


def test_seed_labels_are_auditable():
    base = {"student_text": "RAG là gì", "tutor_text": "RAG là retrieval", "move_used": "review_concept"}
    assert seed_label(base) == "student_stuck"
    base["tutor_text"] = "Xin lỗi, tôi không tìm thấy nội dung cụ thể"
    assert seed_label(base) == "chat_cannot_help"
    base["student_text"] = "hello"
    assert seed_label(base) == "irrelevant_question"


def test_topic_detection():
    assert topic_for("ReAct agent hoạt động ra sao?") == "agent / ReAct"


def test_phobert_input_contains_all_turn_parts():
    text = PhoBERTTextClassifier.format_text({
        "student_text": "Agent là gì?", "selected_text": "Agent dùng tool",
        "tutor_text": "Agent thực hiện nhiều bước.",
    })
    assert "Câu hỏi học viên: Agent là gì?" in text
    assert "Đoạn được chọn: Agent dùng tool" in text
    assert "Câu trả lời gia sư: Agent thực hiện nhiều bước." in text
