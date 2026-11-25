"""Doc va kiem form multipart cua POST /api/voice/transcribe (contract voice-service-api.md).

Thu tu kiem (de khong ton credit / khong gui audio di khi request sai): dong y -> truong tuy chon -> co tep audio.
Route doc form bang tay (request.form()) de dieu khien thu tu nay; OPENAPI_REQUEST_BODY mo ta form cho Swagger.
"""
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

from starlette.datastructures import FormData, UploadFile

from .api_error import ApiError
from .audio_validation import parse_client_time
from .config import Settings

LANGUAGES = ("vi", "en")
MAX_TOPIC_ID_CHARS = 200

OPENAPI_REQUEST_BODY = {"requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
    "type": "object", "required": ["audio", "consent_confirmed"], "properties": {
        "audio": {"type": "string", "format": "binary", "description": "webm / ogg / wav / mp3 / m4a"},
        "consent_confirmed": {"type": "string", "enum": ["true"], "description": "Ben goi xac nhan da co dong y (FR-024)"},
        "keywords": {"type": "array", "items": {"type": "string"}, "description": "Lap truong, hoac mot JSON array"},
        "question_audio_ended_at": {"type": "string", "description": "ISO 8601 hoac epoch ms (dong ho client)"},
        "recording_started_at": {"type": "string", "description": "ISO 8601 hoac epoch ms (dong ho client)"},
        "answer_limit_s": {"type": "number", "exclusiveMinimum": 0},
        "topic_id": {"type": "string"},
        "language": {"type": "string", "enum": list(LANGUAGES), "default": "vi"}}}}}}}


@dataclass(frozen=True)
class TranscribeForm:
    upload: UploadFile
    keywords: List[str]
    keywords_truncated: bool
    question_audio_ended_at: Optional[float]
    recording_started_at: Optional[float]
    timestamps_invalid: bool  # co gui moc nhung khong doc duoc: route them canh bao, thinking_time rong
    answer_limit_s: Optional[float]
    topic_id: Optional[str]
    language: str


def parse_keywords(raw_values: List[str], max_keywords: int) -> Tuple[List[str], bool]:
    """Truong `keywords` lap nhieu lan, hoac mot gia tri la JSON array. Bo rong / trung, giu thu tu, cat o max_keywords."""
    items: List[str] = []
    for raw in raw_values:
        text = raw.strip()
        if text.startswith("["):
            try:
                decoded = json.loads(text)
            except ValueError:
                decoded = None
            if isinstance(decoded, list):
                items.extend(str(x) for x in decoded if isinstance(x, (str, int, float)))
                continue
        items.append(text)
    unique = list(dict.fromkeys(i.strip() for i in items if i and i.strip()))
    return unique[:max_keywords], len(unique) > max_keywords


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(400, "invalid_request", f"{field}: {message}", {"field": field})


def parse_transcribe_form(form: FormData, settings: Settings) -> TranscribeForm:
    if str(form.get("consent_confirmed") or "").strip().lower() != "true":
        raise ApiError(400, "consent_required",
                       "Cần xác nhận ứng viên đã đồng ý dùng micro và xử lý giọng nói (consent_confirmed=true)")
    language = str(form.get("language") or "vi").strip().lower()
    if language not in LANGUAGES:
        raise _invalid("language", "chỉ nhận vi hoặc en")
    limit_raw = str(form.get("answer_limit_s") or "").strip()
    limit: Optional[float] = None
    if limit_raw:
        try:
            limit = float(limit_raw)
        except ValueError:
            limit = None
        if limit is None or not 0 < limit < float("inf"):
            raise _invalid("answer_limit_s", "cần số lớn hơn 0")
    topic_id = str(form.get("topic_id") or "").strip() or None
    if topic_id and len(topic_id) > MAX_TOPIC_ID_CHARS:
        raise _invalid("topic_id", f"tối đa {MAX_TOPIC_ID_CHARS} ký tự")
    upload = form.get("audio")
    if not isinstance(upload, UploadFile):
        raise _invalid("audio", "thiếu tệp âm thanh")

    times, invalid = [], False
    for name in ("question_audio_ended_at", "recording_started_at"):
        try:
            times.append(parse_client_time(str(form.get(name) or "")))
        except ValueError:
            times.append(None)
            invalid = True
    keywords, truncated = parse_keywords([str(v) for v in form.getlist("keywords")], settings.max_keywords)
    return TranscribeForm(upload, keywords, truncated, times[0], times[1], invalid, limit, topic_id, language)
