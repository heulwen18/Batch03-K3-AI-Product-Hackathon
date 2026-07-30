"""Xây dựng index tìm kiếm cho 1 file học viên TỰ UPLOAD (PDF/PPTX/TXT/MD) — cùng khuôn dạng
(code, normalized_body, original_body) với transcript_index.load_transcript_paragraphs(), nên
transcript_index.search() dùng lại được y nguyên, không cần đổi gì ở agent_tutor.py.

Vẫn giữ nguyên tắc rule-based/kiểm lại được: keyword-overlap, không embedding, không gọi AI
ở bước index hoá — AI chỉ tham gia ở bước trả lời câu hỏi (agent_tutor.py).

Chia theo TRANG (PDF) / SLIDE (PPTX) làm đơn vị trích dẫn — khớp đúng khái niệm "trang" đã có
sẵn trong sản phẩm (repeated_page, format_question(page=...)).
"""
import io

from transcript_index import normalize


def _paragraphs_from_text(text, prefix="DOAN"):
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paras and text.strip():
        paras = [text.strip()]
    return [(f"{prefix}-{i + 1:02d}", normalize(p), p) for i, p in enumerate(paras)]


def extract_pdf(file_bytes):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("Thiếu thư viện đọc PDF — chạy `pip install pypdf` rồi thử lại.")
    reader = PdfReader(io.BytesIO(file_bytes))
    chunks = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            chunks.append((f"TRANG-{i + 1:02d}", normalize(text), text))
    return chunks


def extract_pptx(file_bytes):
    try:
        from pptx import Presentation
    except ImportError:
        raise RuntimeError("Thiếu thư viện đọc PPTX — chạy `pip install python-pptx` rồi thử lại.")
    prs = Presentation(io.BytesIO(file_bytes))
    chunks = []
    for i, slide in enumerate(prs.slides):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    parts.append(t)
        text = "\n".join(parts).strip()
        if text:
            chunks.append((f"SLIDE-{i + 1:02d}", normalize(text), text))
    return chunks


def build_upload_index(filename, file_bytes):
    """Trả về index cùng khuôn dạng transcript_index — dùng trực tiếp với transcript_index.search().

    Ném RuntimeError/ValueError với thông báo rõ ràng nếu không đọc được (định dạng chưa hỗ trợ,
    thiếu thư viện, hoặc file không có text — vd slide toàn ảnh scan, chưa hỗ trợ OCR).
    """
    name = filename.lower()
    if name.endswith(".pdf"):
        chunks = extract_pdf(file_bytes)
    elif name.endswith(".pptx"):
        chunks = extract_pptx(file_bytes)
    elif name.endswith((".txt", ".md")):
        text = file_bytes.decode("utf-8", errors="ignore")
        chunks = _paragraphs_from_text(text)
    else:
        raise ValueError(f"Định dạng file chưa hỗ trợ: {filename} (chỉ hỗ trợ .pdf, .pptx, .txt, .md)")
    return chunks
