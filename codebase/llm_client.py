"""Client LLM dùng chung cho Khối 2 (classify_friction.py) và Agent A (agent_tutor.py).

Dùng Groq (API tương thích OpenAI, có tool-calling) — đọc GROQ_API_KEY từ file `.env` cùng
thư mục tự động (không cần export tay). File `.env` đã nằm trong .gitignore, không commit.
"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, BadRequestError

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 3  # model thỉnh thoảng sinh sai định dạng tool-call (flaky, đã quan sát thực tế) — retry thường qua


def get_client(api_key=None):
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "Thiếu GROQ_API_KEY — đặt trong codebase/.env (GROQ_API_KEY = ...) "
            "hoặc truyền api_key trực tiếp."
        )
    return Groq(api_key=key)


def create_with_retry(client, **kwargs):
    """Wrapper quanh client.chat.completions.create — retry khi model sinh sai định dạng
    tool-call (groq lỗi code='tool_use_failed'), lỗi này quan sát được là flaky/không nhất
    quán (cùng prompt lúc thành công lúc không), retry lại thường qua ngay.
    """
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except BadRequestError as e:
            last_err = e
            if "tool_use_failed" not in str(e) or attempt == MAX_RETRIES - 1:
                raise
            time.sleep(0.5 * (attempt + 1))
    raise last_err


def to_function_tool(name, description, parameters_schema):
    """Chuyển 1 schema (dạng input_schema JSON-schema thường) -> format tool Groq/OpenAI-compatible."""
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters_schema},
    }
