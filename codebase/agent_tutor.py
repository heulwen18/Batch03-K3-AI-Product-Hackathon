"""AGENT A — Demo tutor ReAct/tool-calling, CHỈ để sinh input sống cho demo.

KHÔNG phải "quyết định AI trung tâm" được chấm (đó vẫn là classify_friction.py / Khối 2).
Agent này mô phỏng cách VLearn tutor thật hoạt động — multi-step tool-use, đúng ghi chú
`llm_call_count` 2-7/turn trong data dictionary (data/vlearn-pack/chatlog/DATA_DICTIONARY.md).

Vòng lặp ReAct: model tự quyết định gọi tool search_transcript (tối đa MAX_TOOL_ROUNDS lần),
đọc kết quả, rồi trả lời — trung thực nói "không tìm thấy" nếu không đủ căn cứ, KHÔNG bịa.
Dùng Groq (OpenAI-compatible tool-calling) qua llm_client.py.
"""
import json

from transcript_index import search as transcript_search
from llm_client import get_client, to_function_tool, create_with_retry, DEFAULT_MODEL

MODEL = DEFAULT_MODEL
MAX_TOOL_ROUNDS = 2  # giới hạn để demo live không bị treo / không tốn quota vô hạn

SEARCH_TOOL = to_function_tool(
    "search_transcript",
    "Tìm đoạn tài liệu khớp với 1 câu hỏi/khái niệm trong nguồn được cấp (transcript bài giảng, "
    "hoặc file học viên vừa upload). Trả về top đoạn khớp nhiều từ khoá nhất kèm mã trích dẫn "
    "và match_ratio (0-1, càng cao càng chắc).",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Từ khoá/câu hỏi cần tìm trong tài liệu."},
        },
        "required": ["query"],
    },
)


def build_system_prompt(source_label="6 buổi giảng được cấp"):
    """source_label mô tả NGUỒN THẬT đang được tra cứu — mặc định 6 buổi giảng có sẵn trong data
    pack, nhưng khi học viên upload file riêng (app.py), phải đổi thành tên file đó để agent không
    nói sai nguồn (vd không được nói "6 buổi giảng" khi đang tra cứu file PDF vừa upload)."""
    return f"""Bạn là AI tutor demo cho khoá học AI thực chiến. Vai trò DUY NHẤT: trả lời câu \
hỏi học viên CHỈ dựa trên nội dung {source_label}, tra cứu qua tool search_transcript.

Quy tắc bắt buộc:
- LUÔN gọi search_transcript trước khi trả lời một câu hỏi về kiến thức — không tự trả lời từ \
  kiến thức nền của bạn.
- Có thể gọi tool tối đa 2 lần/câu hỏi (thử query khác nếu lần đầu chưa đủ chắc, vd match_ratio thấp).
- Nếu sau khi tra cứu vẫn không đủ căn cứ (không có kết quả, hoặc match_ratio đều thấp): trả lời \
  trung thực "Mình không tìm thấy nội dung này trong {source_label} — có thể đã dạy/trình bày ở \
  chỗ khác, bạn nên hỏi lại giảng viên/TA để chắc chắn." KHÔNG bịa câu trả lời từ kiến thức nền chung.
- Nếu tìm thấy (match_ratio đủ cao): trả lời ngắn gọn (2-4 câu), TRÍCH DẪN mã đoạn đã dùng.
- Câu hỏi ngoài phạm vi tài liệu (hỏi về bản thân bạn, thời tiết, chào hỏi xã giao...): trả lời \
  ngắn gọn rằng đây ngoài phạm vi hỗ trợ, không cần gọi tool."""


SYSTEM_PROMPT = build_system_prompt()  # mặc định — giữ tương thích ngược cho dashboard.py/agent_demo_ui.py


def format_question(question, page=None):
    """Thêm ngữ cảnh trang (nếu có) vào câu hỏi — mô phỏng format 'bôi đen' của VLearn thật."""
    if page:
        return f'(Trang {page}) {question}'
    return question


def _tool_calls_to_dict(tool_calls):
    return [
        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
        for tc in tool_calls
    ]


def run_turn(index, history, user_message, api_key=None, model=MODEL, system_prompt=None):
    """history: list message (role/content, KHÔNG gồm system) của các lượt TRƯỚC.

    system_prompt: mặc định None -> dùng SYSTEM_PROMPT (nguồn = 6 buổi giảng). Truyền
    build_system_prompt("tài liệu bạn vừa upload (...)") khi index là nội dung học viên tự upload
    (xem app.py) để agent không nói sai nguồn đang tra cứu.

    Trả về (assistant_text, tool_calls_log, new_history) — new_history cũng KHÔNG gồm system,
    tự thêm lại system prompt ở đầu mỗi lần gọi để tránh lưu trùng lặp qua nhiều lượt.
    """
    system_prompt = system_prompt or SYSTEM_PROMPT
    client = get_client(api_key)
    messages = list(history) + [{"role": "user", "content": user_message}]
    tool_calls_log = []

    # Đúng MAX_TOOL_ROUNDS lượt gọi tool tối đa (không +1 — off-by-one từng khiến vòng lặp
    # thực thi tool tới MAX_TOOL_ROUNDS+1 lần, đã bắt được bằng test mock trước khi tốn quota thật).
    for _ in range(MAX_TOOL_ROUNDS):
        resp = create_with_retry(client,
            model=model,
            max_tokens=800,
            tools=[SEARCH_TOOL],
            tool_choice="auto",
            messages=[{"role": "system", "content": system_prompt}] + messages,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content or "", tool_calls_log, messages

        messages.append({"role": "assistant", "content": msg.content, "tool_calls": _tool_calls_to_dict(msg.tool_calls)})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            query = args.get("query", "")
            results = transcript_search(query, index, k=3)
            tool_calls_log.append({"query": query, "results": results})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(results, ensure_ascii=False) if results else "Không tìm thấy đoạn nào khớp.",
            })

    # Đã dùng hết MAX_TOOL_ROUNDS lượt gọi tool — gọi thêm 1 lần CUỐI, KHÔNG cho tool nữa,
    # ép model tổng hợp câu trả lời từ những gì tool đã trả về thay vì trả 1 câu chung chung.
    resp = create_with_retry(
        client, model=model, max_tokens=800,
        messages=[{"role": "system", "content": system_prompt}] + messages,
    )
    msg = resp.choices[0].message
    messages.append({"role": "assistant", "content": msg.content})
    final_text = msg.content or "Mình cần thêm thông tin để trả lời chắc chắn — bạn hỏi lại rõ hơn giúp mình nhé?"
    return final_text, tool_calls_log, messages


def turn_to_case_format(turn_id, page, question, assistant_text):
    """Chuyển 1 lượt Agent A -> đúng field mà signals.py cần (khớp turn thật trong data_prep.py),
    để hội thoại demo live cũng chạy qua được Khối 1/2 y hệt data lịch sử.
    """
    return {
        'turn_id': turn_id,
        'page': str(page) if page else None,
        'question': question,
        'tutor_content': assistant_text,
        'move_used': None,   # Agent A không có nhãn move sư phạm như tutor thật — không suy diễn
        'citations': [],
        'rating': None,      # không có cơ chế rating trong demo live
    }


if __name__ == '__main__':
    import sys
    from transcript_index import load_transcript_paragraphs

    index = load_transcript_paragraphs('../data/vlearn-pack/transcript')
    if '--live' not in sys.argv:
        print("Dry-run — không gọi AI thật. Chạy `python3 agent_tutor.py --live` với "
              "GROQ_API_KEY trong codebase/.env để test hội thoại thật qua terminal.")
        sys.exit(0)

    print("Agent A demo — gõ câu hỏi (Ctrl+C để thoát). Gõ 'trang:12 <câu hỏi>' để mô phỏng chọn trang.")
    history = []
    while True:
        raw = input("\nHọc viên> ").strip()
        if not raw:
            continue
        page = None
        if raw.startswith('trang:'):
            page, _, raw = raw[6:].partition(' ')
        q = format_question(raw, page)
        answer, log, history = run_turn(index, history, q)
        for t in log:
            print(f"  [tool] search_transcript({t['query']!r}) -> {len(t['results'])} kết quả")
        print(f"Tutor demo> {answer}")
