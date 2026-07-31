from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from collections.abc import Mapping
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "vlearn-pack" / "transcript"
TRACE_PATH = PROJECT_ROOT / "eval" / "gemini_traces.jsonl"
DEFAULT_MODEL = "gemini-3.6-flash"
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SEGMENT_RE = re.compile(
    r"\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*?)(?=\n\s*\*\*\[T|\Z)",
    re.DOTALL,
)
WORD_RE = re.compile(r"[A-Za-zÀ-ỹ0-9+#.]{3,}", re.UNICODE)
STOPWORDS = {
    "anh",
    "ban",
    "bạn",
    "cac",
    "các",
    "cho",
    "cua",
    "của",
    "duoc",
    "được",
    "giai",
    "giải",
    "giup",
    "giúp",
    "hoc",
    "học",
    "khong",
    "không",
    "minh",
    "mình",
    "mot",
    "một",
    "nhung",
    "những",
    "noi",
    "nói",
    "the",
    "thế",
    "trang",
    "trong",
    "voi",
    "với",
}

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Khái niệm học tập chính, tối đa 8 từ.",
        },
        "root_cause": {
            "type": "string",
            "enum": ["content_gap", "retrieval_bug", "learner_difficulty", "off_topic", "uncertain"],
        },
        "severity": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "summary": {
            "type": "string",
            "description": "Tóm tắt tiếng Việt ngắn gọn, có căn cứ.",
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 7,
        },
        "evidence_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": [
        "topic",
        "root_cause",
        "severity",
        "summary",
        "recommendations",
        "tags",
        "evidence_ids",
        "confidence",
    ],
    "additionalProperties": False,
}


class GeminiAnalysisError(RuntimeError):
    """A safe, user-displayable Gemini analysis failure."""


def _read_dotenv_value(name: str) -> str | None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return None
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        env_name, value = line.split("=", 1)
        if env_name.strip() == name:
            return value.strip().strip("\"'")
    return None


def resolve_api_key(secrets: Mapping[str, Any] | None = None) -> str | None:
    """Resolve the key without ever logging or returning its source."""
    if secrets is not None:
        try:
            for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                value = str(secrets.get(name, "")).strip()
                if value:
                    return value
        except FileNotFoundError:
            # Streamlit raises StreamlitSecretNotFoundError (a FileNotFoundError)
            # when the app is launched from a directory without secrets.toml.
            pass

    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(name, "").strip() or (_read_dotenv_value(name) or "")
        if value:
            return value
    return None


def _tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in WORD_RE.findall(text)
        if token.casefold() not in STOPWORDS
    }


@lru_cache(maxsize=1)
def load_transcript_segments() -> tuple[dict[str, str], ...]:
    segments: list[dict[str, str]] = []
    if not TRANSCRIPT_DIR.exists():
        return ()
    for path in sorted(TRANSCRIPT_DIR.glob("transcript-*-clean.md")):
        content = path.read_text(encoding="utf-8")
        for segment_id, text in SEGMENT_RE.findall(content):
            clean_text = " ".join(text.split())
            segments.append(
                {
                    "segment_id": segment_id,
                    "text": clean_text,
                    "source": path.name,
                }
            )
    return tuple(segments)


def retrieve_transcript_evidence(query: str, limit: int = 3) -> list[dict[str, str]]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    ranked: list[tuple[float, dict[str, str]]] = []
    for segment in load_transcript_segments():
        segment_tokens = _tokens(segment["text"])
        overlap = query_tokens & segment_tokens
        if not overlap:
            continue
        score = len(overlap) / max(len(query_tokens), 1)
        score += 0.15 * len(overlap) / max(len(segment_tokens), 1)
        ranked.append((score, segment))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [dict(segment) for _, segment in ranked[:limit]]


def _build_prompt(
    conversation_id: str,
    fixed_category: str,
    messages: list[dict[str, str]],
    evidence: list[dict[str, str]],
) -> str:
    transcript = "\n".join(
        f"[{message.get('role', 'unknown')}] {message.get('content', '')[:3500]}"
        for message in messages
    )
    evidence_text = "\n".join(
        f"[{item['segment_id']}] {item['text'][:1800]}" for item in evidence
    )
    if not evidence_text:
        evidence_text = "(Không tìm thấy đoạn transcript liên quan đủ mạnh.)"

    return f"""
Bạn là AI Learning Analytics Copilot cho giảng viên.

Nhiệm vụ: phân tích hội thoại để xác định chủ đề, nguyên nhân gốc, mức độ,
tóm tắt và tối đa 3 hành động cụ thể cho giảng viên.

RÀNG BUỘC BẮT BUỘC:
- Nhóm friction đã được hệ thống rule-based khóa là "{fixed_category}".
- Không được đổi hoặc suy diễn lại nhóm friction này.
- Chỉ dùng bằng chứng transcript được cung cấp bên dưới.
- evidence_ids chỉ được chứa mã nằm trong phần bằng chứng.
- Nếu bằng chứng không đủ, chọn root_cause="uncertain", confidence <= 0.55,
  và nói rõ giới hạn trong summary.
- Không khẳng định một khái niệm "chưa từng được dạy"; chỉ được nói không thấy
  trong các transcript được cung cấp.
- Trả lời bằng tiếng Việt, ngắn gọn, phù hợp để hiển thị trên dashboard.

Conversation ID: {conversation_id}

HỘI THOẠI:
{transcript}

BẰNG CHỨNG TRANSCRIPT:
{evidence_text}
""".strip()


def _response_text(payload: dict[str, Any]) -> str:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        return "".join(
            part.get("text", "")
            for part in parts
            if not part.get("thought", False)
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiAnalysisError("Gemini không trả về nội dung phân tích.") from exc


def _normalize_result(
    raw: dict[str, Any],
    evidence: list[dict[str, str]],
) -> dict[str, Any]:
    valid_causes = {
        "content_gap",
        "retrieval_bug",
        "learner_difficulty",
        "off_topic",
        "uncertain",
    }
    valid_severities = {"low", "medium", "high"}
    available_evidence = {item["segment_id"]: item for item in evidence}

    cause = str(raw.get("root_cause", "uncertain"))
    severity = str(raw.get("severity", "low"))
    recommendations = [
        str(item).strip()
        for item in raw.get("recommendations", [])
        if str(item).strip()
    ][:3]
    tags = [str(item).strip() for item in raw.get("tags", []) if str(item).strip()][:7]
    evidence_ids = [
        str(item)
        for item in raw.get("evidence_ids", [])
        if str(item) in available_evidence
    ][:3]
    try:
        confidence = min(1.0, max(0.0, float(raw.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "topic": str(raw.get("topic", "Chưa xác định")).strip() or "Chưa xác định",
        "root_cause": cause if cause in valid_causes else "uncertain",
        "severity": severity if severity in valid_severities else "low",
        "summary": str(raw.get("summary", "Chưa có kết luận.")).strip(),
        "recommendations": recommendations or ["Giảng viên kiểm tra lại hội thoại và tài liệu liên quan."],
        "tags": tags,
        "evidence_ids": evidence_ids,
        "evidence": [available_evidence[item] for item in evidence_ids],
        "confidence": confidence,
    }


def _write_trace(
    conversation_id: str,
    model: str,
    prompt: str,
    result: dict[str, Any],
) -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    trace = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "conversation_id": conversation_id,
        "model": model,
        "input_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "result": {
            key: value
            for key, value in result.items()
            if key != "evidence"
        },
    }
    with TRACE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace, ensure_ascii=False) + "\n")


def analyze_conversation(
    conversation_id: str,
    fixed_category: str,
    messages: list[dict[str, str]],
    *,
    api_key: str,
    model: str | None = None,
) -> dict[str, Any]:
    model_name = (
        model
        or os.getenv("GEMINI_MODEL")
        or _read_dotenv_value("GEMINI_MODEL")
        or DEFAULT_MODEL
    ).strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", model_name):
        raise GeminiAnalysisError("Tên GEMINI_MODEL không hợp lệ.")

    query = " ".join(message.get("content", "") for message in messages)
    evidence = retrieve_transcript_evidence(query, limit=3)
    prompt = _build_prompt(conversation_id, fixed_category, messages, evidence)
    request_body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1200,
            "responseMimeType": "application/json",
            "responseJsonSchema": OUTPUT_SCHEMA,
        },
    }

    try:
        response = requests.post(
            GEMINI_ENDPOINT.format(model=model_name),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            json=request_body,
            timeout=(10, 60),
        )
    except requests.RequestException as exc:
        raise GeminiAnalysisError("Không kết nối được Gemini API.") from exc

    if response.status_code == 401:
        raise GeminiAnalysisError(
            "GEMINI_API_KEY không hợp lệ hoặc đã hết hiệu lực. "
            "Hãy tạo/copy key từ Google AI Studio, cập nhật secret rồi khởi động lại app."
        )
    if response.status_code == 403:
        raise GeminiAnalysisError(
            "API key không có quyền gọi Gemini API. "
            "Hãy kiểm tra project, trạng thái billing và giới hạn API key trong Google AI Studio."
        )
    if not response.ok:
        detail = response.text.replace("\n", " ")[:240]
        raise GeminiAnalysisError(
            f"Gemini API trả về lỗi {response.status_code}: {detail}"
        )

    try:
        raw_result = json.loads(_response_text(response.json()))
    except (json.JSONDecodeError, ValueError) as exc:
        raise GeminiAnalysisError("Gemini trả về JSON không hợp lệ.") from exc

    result = _normalize_result(raw_result, evidence)
    _write_trace(conversation_id, model_name, prompt, result)
    return result
