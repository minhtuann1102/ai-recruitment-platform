"""Kiem tra tep am thanh truoc khi gui nha cung cap (research R6) va doc moc thoi gian client.

- Dinh dang cho phep: webm, ogg, wav, mp3, m4a (theo duoi tep, khong co duoi thi theo content-type).
- Kich thuoc <= VOICE_MAX_UPLOAD_MB (413 audio_too_long); tep rong / sai loai -> 415 invalid_audio.
- Audio chi nam trong bo nho (FR-015): keep_uploads_in_memory chinh nguong cuon ra dia cua Starlette, con
  reject_oversized_body tu choi body qua lon TRUOC khi parse multipart (khong thi phan vuot nguong van ra dia).
"""
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Optional

from starlette.formparsers import MultiPartParser

from .api_error import ApiError

EXT_CONTENT_TYPE = {".webm": "audio/webm", ".ogg": "audio/ogg", ".wav": "audio/wav", ".mp3": "audio/mpeg",
                    ".m4a": "audio/mp4"}
CONTENT_TYPE_EXT = {"audio/webm": ".webm", "video/webm": ".webm", "audio/ogg": ".ogg", "application/ogg": ".ogg",
                    "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/wave": ".wav", "audio/mpeg": ".mp3",
                    "audio/mp3": ".mp3", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/m4a": ".m4a"}
MULTIPART_MARGIN_BYTES = 64 * 1024  # truong form + bien multipart ngoai tep audio


@dataclass(frozen=True)
class ValidatedAudio:
    data: bytes
    filename: str  # chuan hoa "audio<.ext>": khong chuyen ten tep that cua nguoi dung cho nha cung cap
    content_type: str


def validate_audio(filename: Optional[str], content_type: Optional[str], data: bytes, max_bytes: int) -> ValidatedAudio:
    ext = PurePosixPath(filename or "").suffix.lower()
    if ext not in EXT_CONTENT_TYPE:
        ext = CONTENT_TYPE_EXT.get((content_type or "").split(";")[0].strip().lower(), "")
    if not ext:
        raise ApiError(415, "invalid_audio", "Định dạng âm thanh không được hỗ trợ (webm, ogg, wav, mp3, m4a)",
                       {"allowed": sorted(e.lstrip(".") for e in EXT_CONTENT_TYPE)})
    if not data:
        raise ApiError(415, "invalid_audio", "Tệp âm thanh rỗng")
    if len(data) > max_bytes:
        raise ApiError(413, "audio_too_long", "Tệp âm thanh vượt giới hạn dung lượng",
                       {"max_bytes": max_bytes, "size_bytes": len(data)})
    return ValidatedAudio(data, f"audio{ext}", EXT_CONTENT_TYPE[ext])


def keep_uploads_in_memory(max_upload_bytes: int) -> None:
    """Starlette cuon phan tep > nguong (mac dinh 1 MB) ra tep tam tren dia: dat nguong >= gioi han upload de audio
    hop le khong bao gio cham dia. Ten thuoc tinh doi theo ban Starlette (max_file_size / spool_max_size)."""
    for attr in ("spool_max_size", "max_file_size"):
        if hasattr(MultiPartParser, attr):
            setattr(MultiPartParser, attr, max_upload_bytes + MULTIPART_MARGIN_BYTES)


def reject_oversized_body(content_length: Optional[str], max_upload_bytes: int) -> None:
    """413 neu Content-Length vuot gioi han + bien multipart, goi truoc request.form(). Khong co / sai header: bo qua."""
    try:
        size = int(content_length or "")
    except ValueError:
        return
    if size > max_upload_bytes + MULTIPART_MARGIN_BYTES:
        raise ApiError(413, "audio_too_long", "Yêu cầu vượt giới hạn dung lượng âm thanh",
                       {"max_bytes": max_upload_bytes})


def parse_client_time(raw: Optional[str]) -> Optional[float]:
    """Moc dong ho client -> epoch giay. ISO 8601 (khong co mui gio = UTC) hoac epoch mili giay. Rong / None -> None.
    ValueError neu co gia tri nhung khong doc duoc (route doi thanh canh bao invalid_client_timestamps)."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        value = float(text) / 1000.0
    except ValueError:
        parsed = datetime.fromisoformat(text)  # ValueError neu sai dinh dang
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    if not math.isfinite(value):
        raise ValueError("moc thoi gian khong huu han")
    return value
