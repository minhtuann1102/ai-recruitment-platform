"""Doi loi tra ve cua Blaze sang ApiError cua voice-service (research R8).

Body loi cua Blaze: {"error": {"message", "type", "code", "param"}}. Chi lay `code` va `type` (chuoi ngan) dua vao
`details`; KHONG chep `message` cua nha cung cap (co the lap lai noi dung request). Chua tung thay body loi that cua
Blaze (spike khong cham 402 / 429): QUOTA_MARKERS la phong doan, chua xac minh cho toi khi co body loi that.
"""
import json
from typing import Tuple

from .api_error import ApiError

# 429 co ma loi chua mot trong cac chuoi nay = het credit (khong thu lai); 429 khac = vuot toc do (thu lai)
QUOTA_MARKERS = ("insufficient", "quota", "credit", "balance")
# 400 / 415 / 422 cua cac endpoint nhan file = file am thanh khong dung
AUDIO_REJECTED_STATUSES = (400, 415, 422)


def read_error_fields(body: bytes) -> Tuple[str, str, str]:
    """(code, type, message) tu body loi cua Blaze, rong neu khong doc duoc. Chuoi viet thuong, cat ngan."""
    try:
        err = json.loads(body).get("error")
    except (ValueError, AttributeError):
        return "", "", ""
    if not isinstance(err, dict):
        return "", "", ""
    return tuple(str(err.get(k) or "").lower()[:200] for k in ("code", "type", "message"))  # type: ignore[return-value]


def is_quota_error(status: int, body: bytes) -> bool:
    """402 luon la het credit; 429 chi khi ma / loai / thong diep loi co dau hieu het han muc."""
    if status == 402:
        return True
    if status != 429:
        return False
    return any(marker in field for field in read_error_fields(body) for marker in QUOTA_MARKERS)


def is_retryable(status: int, body: bytes) -> bool:
    """Chi 503 (qua tai, chua xu ly) va 429 khong phai het credit moi thu lai. KHONG thu lai 500 / 502 / 504: nha cung cap
    co the da nhan va tinh phi request, gui lai se tinh phi lan nua (H1 review 2026-11-25)."""
    return status == 503 or (status == 429 and not is_quota_error(status, body))


def map_status_error(status: int, body: bytes, audio: bool) -> ApiError:
    """ApiError cho ma HTTP loi (>= 400) cua Blaze. `audio` = endpoint nhan file (VAD / STT)."""
    code, kind, _ = read_error_fields(body)
    details = {"provider_status": status, "provider_code": code or kind or None}
    if is_quota_error(status, body):
        return ApiError(402, "quota_exceeded", "Tài khoản nhà cung cấp giọng nói đã hết hạn mức", details)
    if status == 429:
        return ApiError(429, "provider_rate_limited", "Nhà cung cấp giọng nói đang giới hạn tốc độ, thử lại sau", details)
    if status in (401, 403):  # key Blaze sai / het han: loi cau hinh phia server, khong phai loi cua nguoi goi
        return ApiError(502, "provider_error", "Nhà cung cấp giọng nói từ chối khóa truy cập của dịch vụ", details)
    if audio and status == 413:
        return ApiError(413, "audio_too_long", "Nhà cung cấp từ chối vì tệp âm thanh quá lớn", details)
    if audio and status in AUDIO_REJECTED_STATUSES:
        return ApiError(415, "invalid_audio", "Nhà cung cấp không nhận được tệp âm thanh này", details)
    return ApiError(502, "provider_error", "Nhà cung cấp giọng nói gặp lỗi", details)
