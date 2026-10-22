"""Chi nhan request noi bo (FR-AI-091): moi endpoint tru /api/health can header X-Internal-Token.

Token lay tu bien moi truong AI_SERVICE_INTERNAL_TOKEN, so sanh hang thoi gian. Chua dat AI_SERVICE_INTERNAL_TOKEN (may dev, CI)
thi khong kiem va ghi canh bao mot lan; moi truong staging/demo PHAI dat.
"""
import hmac
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("ai_service.security")
OPEN_PATHS = {"/api/health"}
HEADER = "X-Internal-Token"
_warned = False


async def internal_token_middleware(request: Request, call_next):
    global _warned
    expected = os.environ.get("AI_SERVICE_INTERNAL_TOKEN", "")
    if not expected:
        if not _warned:
            log.warning("AI_SERVICE_INTERNAL_TOKEN chua dat: ai-service dang nhan request khong xac thuc (chi dung cho dev)")
            _warned = True
        return await call_next(request)
    if request.url.path in OPEN_PATHS:
        return await call_next(request)
    given = request.headers.get(HEADER, "")
    if not hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Thiếu hoặc sai X-Internal-Token",
                                                      "details": None})
    return await call_next(request)
