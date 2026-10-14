"""Dinh dang Server-Sent Events cho /api/start va /api/next-turn (docs/ai-service/06 muc 7.4, 7.5)."""
import asyncio
import json
import os
import re
from typing import AsyncIterator, Dict, Optional

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def event(name: str, data: Dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def chunk_tokens(text: str, words_per_token: int = 3):
    """Cat cau hoi thanh cac manh nho giu nguyen khoang trang, de mo phong stream token."""
    parts = re.findall(r"\S+\s*", text)
    return ["".join(parts[i:i + words_per_token]) for i in range(0, len(parts), words_per_token)]


async def stream_events(meta: Optional[Dict], question: Optional[str], done: Dict) -> AsyncIterator[str]:
    """meta -> token... -> done. Loi bat ngo gui event error (retryable) thay vi cat ket noi im lang."""
    delay = float(os.getenv("MOCK_STREAM_DELAY_MS", "0")) / 1000
    try:
        if meta:
            yield event("meta", meta)
        for tok in chunk_tokens(question or ""):
            yield event("token", {"t": tok})
            if delay:
                await asyncio.sleep(delay)
        yield event("done", done)
    except Exception:
        yield event("error", {"errorCode": "AI_SERVICE_ERROR", "message": "AI tạm thời không phản hồi",
                              "retryable": True})
