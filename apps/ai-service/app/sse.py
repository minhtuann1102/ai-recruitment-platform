"""Dinh dang Server-Sent Events cho /api/start va /api/next-turn (docs/ai-service/06 muc 7.4, 7.5).

Luong event (meta, token, replace, done, error) dung o main._stream + question_stream."""
import json
import re
from typing import Dict

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def event(name: str, data: Dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def chunk_tokens(text: str, words_per_token: int = 3):
    """Cat cau hoi thanh cac manh nho giu nguyen khoang trang, de mo phong stream token."""
    parts = re.findall(r"\S+\s*", text)
    return ["".join(parts[i:i + words_per_token]) for i in range(0, len(parts), words_per_token)]
