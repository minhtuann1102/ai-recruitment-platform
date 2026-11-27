"""Proxy voice-service cho trang dev /dev/interview (chi khi APP_ENV khong phai staging/production).

Trinh duyet khong goi thang voice-service duoc: voice-service khong mo CORS va giu token noi bo phia server
(VOICE_SERVICE_INTERNAL_TOKEN). Trang dev dong vai interview-service nen ai-service chuyen tiep 4 endpoint:
  GET  /dev/voice/health          -> GET  /api/health
  POST /dev/voice/transcribe      -> POST /api/voice/transcribe   (multipart, chuyen nguyen byte: co Content-Length)
  POST /dev/voice/speak           -> POST /api/voice/speak        (stream audio/mpeg ve trinh duyet)
  POST /dev/voice/session-summary -> POST /api/voice/session-summary
Cac duong POST van sau X-Internal-Token cua ai-service (security.py): Blaze tinh phi theo tung file audio.
Loi cua voice-service tra nguyen ma HTTP + JSON; khong ket noi duoc thi 502 voice_service_unreachable.
"""
import os

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from starlette.background import BackgroundTask

from .api_error import ApiError
from .dev_play_page import ensure_dev

MAX_BODY_BYTES = 11 * 1024 * 1024  # VOICE_MAX_UPLOAD_MB mac dinh 10 MB + phan multipart; voice-service van kiem lai
MAX_JSON_BYTES = 256 * 1024  # speak (<= 1000 ky tu) va session-summary (<= 200 luot) nho hon nhieu
TIMEOUT = httpx.Timeout(60.0, connect=5.0)  # STT cua Blaze toi 30 s (VOICE_PROVIDER_TIMEOUT_S) + thu lai
router = APIRouter(include_in_schema=False)


def _base_url() -> str:
    return os.environ.get("VOICE_SERVICE_URL", "http://localhost:8020").rstrip("/")


def _headers(content_type: str | None = None) -> dict:
    h = {}
    token = os.environ.get("VOICE_SERVICE_INTERNAL_TOKEN", "")
    if token:  # may dev chua dat token cho voice-service thi khong gui
        h["X-Internal-Token"] = token
    if content_type:
        h["Content-Type"] = content_type
    return h


def _upstream_error(err: httpx.HTTPError) -> ApiError:
    if isinstance(err, httpx.TimeoutException):  # request co the da toi Blaze (da tinh phi): khong bao "chua chay"
        return ApiError(504, "voice_service_timeout", "voice-service không trả lời kịp (có thể đã gọi Blaze): thử lại sau",
                        {"reason": type(err).__name__})
    return ApiError(502, "voice_service_unreachable",
                    f"Không gọi được voice-service ở {_base_url()}: chạy voice-service (cổng 8020) rồi thử lại",
                    {"reason": type(err).__name__})


def _guard(request: Request, json_body: bool = False) -> None:
    """Chi dev; chan trang web khac goi proxy tu trinh duyet (may dev de trong token thi moi request deu qua):
    trinh duyet gui Sec-Fetch-Site, POST text/plain lien site khong can preflight nen bat buoc JSON."""
    ensure_dev()
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise ApiError(403, "forbidden", "Proxy voice chỉ nhận request từ trang /dev/interview")
    if json_body and not request.headers.get("content-type", "").startswith("application/json"):
        raise ApiError(415, "unsupported_media_type", "Body phải là application/json")


async def _forward(method: str, path: str, body: bytes | None = None, content_type: str | None = None) -> Response:
    """Goi voice-service, doc het response (JSON nho) va tra nguyen ma + body."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.request(method, _base_url() + path, content=body, headers=_headers(content_type))
    except httpx.HTTPError as err:
        raise _upstream_error(err) from err
    return Response(r.content, status_code=r.status_code, media_type=r.headers.get("content-type"))


async def _read_limited(request: Request, limit: int) -> bytes:
    """Body cua trinh duyet (fetch luon co Content-Length); chan som khi qua lon de khong giu nhieu MB trong RAM."""
    declared = request.headers.get("content-length")
    if declared is None:
        raise ApiError(411, "length_required", "Request cần Content-Length")
    if not declared.isdigit():
        raise ApiError(400, "invalid_request", "Content-Length không hợp lệ")
    if int(declared) > limit:
        raise ApiError(413, "audio_too_long" if limit == MAX_BODY_BYTES else "body_too_large", "Request quá lớn")
    return await request.body()


@router.get("/dev/voice/health")
async def voice_health(request: Request) -> Response:
    _guard(request)
    return await _forward("GET", "/api/health")


@router.post("/dev/voice/transcribe")
async def voice_transcribe(request: Request) -> Response:
    _guard(request)
    body = await _read_limited(request, MAX_BODY_BYTES)  # nguyen byte + boundary: httpx dat Content-Length
    return await _forward("POST", "/api/voice/transcribe", body, request.headers.get("content-type"))


@router.post("/dev/voice/session-summary")
async def voice_session_summary(request: Request) -> Response:
    _guard(request, json_body=True)
    body = await _read_limited(request, MAX_JSON_BYTES)
    return await _forward("POST", "/api/voice/session-summary", body, "application/json")


@router.post("/dev/voice/speak")
async def voice_speak(request: Request) -> Response:
    """Stream audio/mpeg ve trinh duyet. Loi truoc khi stream thi tra JSON loi nguyen ven."""
    _guard(request, json_body=True)
    body = await _read_limited(request, MAX_JSON_BYTES)
    client = httpx.AsyncClient(timeout=TIMEOUT)
    closed = False

    async def close() -> None:  # goi tu finally cua stream va BackgroundTask: dong mot lan, khong ro ri client
        nonlocal closed
        if not closed:
            closed = True
            await client.aclose()

    try:
        req = client.build_request("POST", _base_url() + "/api/voice/speak", content=body,
                                   headers=_headers("application/json"))
        upstream = await client.send(req, stream=True)
        if upstream.status_code != 200:
            content = await upstream.aread()
            await close()
            return Response(content, status_code=upstream.status_code, media_type=upstream.headers.get("content-type"))
    except httpx.HTTPError as err:
        await close()
        raise _upstream_error(err) from err

    async def chunks():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:  # loi giua stream (Starlette khong chay background khi stream nem loi) hoac xong binh thuong
            await close()
    return StreamingResponse(chunks(), media_type="audio/mpeg", background=BackgroundTask(close))
