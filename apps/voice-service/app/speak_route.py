"""POST /api/voice/speak: van ban cau hoi -> stream audio/mpeg tu TTS Blaze (FR-009, FR-010).

Kiem dau vao (text rong / qua dai / giong la) TRUOC khi goi nha cung cap. Loi truoc byte dau (status loi cua Blaze, khong co
am thanh) tra JSON; sau do la StreamingResponse, loi giua chung chi dong stream. Khong log van ban cau hoi.
Blaze tra content-type audio/mp3; endpoint nay luon tra audio/mpeg (contract).
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from . import metrics
from .api_error import ApiError
from .app_state import get_settings, require_blaze
from .models import SpeakRequest
from .openapi_docs import SPEAK_ERRORS, error_responses

log = logging.getLogger("voice_service")
router = APIRouter()


@router.post("/api/voice/speak", response_class=StreamingResponse, responses={
    200: {"description": "Stream mp3 (chunked)", "content": {"audio/mpeg": {"schema": {"type": "string", "format": "binary"}}}},
    **error_responses(SPEAK_ERRORS)})
async def speak(body: SpeakRequest, request: Request) -> StreamingResponse:
    settings = get_settings(request)
    text = body.text.strip()
    if not text:
        raise ApiError(400, "invalid_request", "text: văn bản không được rỗng", {"field": "text"})
    if len(text) > settings.max_tts_chars:
        raise ApiError(400, "text_too_long", f"Văn bản dài hơn {settings.max_tts_chars} ký tự",
                       {"max_chars": settings.max_tts_chars, "chars": len(text)})
    voice = (body.voice or "").strip() or settings.default_voice
    if voice not in settings.tts_voices:
        raise ApiError(400, "invalid_voice", "Giọng đọc không có trong danh sách cho phép",
                       {"allowed": list(settings.tts_voices)})
    blaze = require_blaze(request)

    stream, first_byte_ms = await metrics.timed("tts", blaze.speak_stream(text, voice))
    log.info("speak_started chars=%d voice=%s first_byte_ms=%d", len(text), voice, first_byte_ms)
    return StreamingResponse(stream, media_type="audio/mpeg", background=BackgroundTask(stream.aclose),
                             headers={"Cache-Control": "no-store"})
