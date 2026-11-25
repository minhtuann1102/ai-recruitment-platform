"""Chi nhan request noi bo (FR-014): moi endpoint tru /api/health va /metrics can header X-Internal-Token.

Token lay tu VOICE_SERVICE_INTERNAL_TOKEN (Settings.internal_token), so sanh hang thoi gian. Chua dat token (may dev, CI)
thi khong kiem va ghi canh bao mot lan; APP_ENV la staging/production ma thieu token thi tra 503 (fail closed).
Mau: apps/ai-service/app/security.py. Khac ai-service: /metrics mo (chi so dem va thoi gian, khong noi dung).
"""
import hmac
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("voice_service.security")
OPEN_PATHS = {"/api/health", "/metrics"}
HEADER = "X-Internal-Token"
_warned = False


async def internal_token_middleware(request: Request, call_next):
    global _warned
    settings = request.app.state.settings
    expected = settings.internal_token
    if request.url.path in OPEN_PATHS:
        return await call_next(request)
    if not expected and settings.strict_env:
        # staging/production ma quen dat token: dong cua thay vi mo toan bo endpoint (fail closed)
        request.state.error_code = "misconfigured"
        return JSONResponse(status_code=503, content={"error": "misconfigured",
                                                      "message": "voice-service chưa cấu hình token nội bộ",
                                                      "details": {}})
    if not expected:
        if not _warned:
            log.warning("internal_token_unset VOICE_SERVICE_INTERNAL_TOKEN chua dat: dang nhan request khong xac thuc "
                        "(chi dung cho dev)")
            _warned = True
        return await call_next(request)
    given = request.headers.get(HEADER, "")
    if not hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        request.state.error_code = "unauthorized"
        return JSONResponse(status_code=401, content={"error": "unauthorized",
                                                      "message": "Thiếu hoặc sai X-Internal-Token", "details": {}})
    return await call_next(request)
