"""Client LLM dùng chung cho classify_friction.py (phân tích) và agent_tutor.py (tutor demo).

Dùng Groq (API tương thích OpenAI, có tool-calling) — đọc GROQ_API_KEY từ file `.env` cùng
thư mục tự động (không cần export tay). File `.env` đã nằm trong .gitignore, không commit.

Quota free tier tính RIÊNG cho từng model (100K token/ngày/model) — nên khi model chính hết
quota ngày (lỗi 429 rate_limit_exceeded loại 'tokens'), tự fallback sang model dự phòng thay
vì chết cứng giữa demo. Đổi model chính bằng biến GROQ_MODEL trong .env nếu cần.
"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, BadRequestError, RateLimitError

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
# Model dự phòng khi model chính hết quota NGÀY — nhỏ hơn (chất lượng đặt tên/tổng hợp kém hơn
# một chút) nhưng có quota riêng, đủ để demo không bị đứng. Vẫn hỗ trợ tool-calling.
FALLBACK_MODEL = os.environ.get("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
MAX_RETRIES = 3  # model thỉnh thoảng sinh sai định dạng tool-call (flaky, đã quan sát thực tế) — retry thường qua


def get_client(api_key=None):
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "Thiếu GROQ_API_KEY — đặt trong codebase/.env (GROQ_API_KEY = ...) "
            "hoặc truyền api_key trực tiếp."
        )
    return Groq(api_key=key)


def _is_daily_quota_error(err):
    s = str(err)
    return "rate_limit_exceeded" in s and ("per day" in s or "TPD" in s or "tokens" in s)


def create_with_retry(client, **kwargs):
    """Wrapper quanh client.chat.completions.create với 2 lớp chống chết giữa demo:

    1. Retry khi model sinh sai định dạng tool-call (lỗi code='tool_use_failed' — flaky,
       cùng prompt lúc thành công lúc không; retry lại thường qua ngay).
    2. Model chính hết quota NGÀY (429 loại 'tokens') -> tự đổi sang FALLBACK_MODEL
       (quota Groq tính riêng từng model). Nếu fallback cũng hết -> báo lỗi rõ ràng
       "hết quota ngày, chờ reset hoặc đổi key" thay vì thông báo mơ hồ.
    """
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as e:
            if _is_daily_quota_error(e) and kwargs.get("model") != FALLBACK_MODEL:
                kwargs["model"] = FALLBACK_MODEL  # thử lại ngay bằng model dự phòng
                last_err = e
                continue
            raise RuntimeError(
                "Groq hết quota (rate limit). Nếu là quota NGÀY (TPD): chờ tới giờ reset trong "
                "thông báo gốc, hoặc đổi GROQ_API_KEY khác trong codebase/.env, hoặc đặt "
                f"GROQ_MODEL sang model còn quota. Lỗi gốc: {e}"
            ) from e
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
