"""So lieu Prometheus (GET /metrics): so request, thoi gian goi nha cung cap, giay audio da xu ly.

Chi dem va do thoi gian, nhan chi co endpoint / ma / ten loi (khong noi dung, khong ma phien) de khong no chuoi thoi
gian. Dinh nghia o muc module (mot lan) nen tao nhieu app trong test khong bi loi "Duplicated timeseries".
Dung REGISTRY mac dinh: Dockerfile chay mot process uvicorn.
"""
import time
from typing import Awaitable, Tuple, TypeVar

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, disable_created_metrics, generate_latest

disable_created_metrics()  # bo series *_created: khong dung, chi lam day /metrics
_PROVIDER_BUCKETS = (0.1, 0.25, 0.5, 1, 1.5, 2, 3, 5, 8, 13, 30)  # giay
KNOWN_ENDPOINTS = {"/api/health", "/api/voice/transcribe", "/api/voice/speak", "/api/voice/session-summary"}

REQUESTS = Counter("voice_requests_total", "Request da xong theo endpoint, status ok/error va ma loi", ["endpoint", "status", "error"])
PROVIDER_SECONDS = Histogram("voice_provider_seconds", "Thoi gian mot lan goi Blaze: vad / stt / tts (tts = toi byte dau tien)",
                             ["call"], buckets=_PROVIDER_BUCKETS)
AUDIO_SECONDS = Counter("voice_audio_seconds_total", "Giay audio da xu ly (uoc luong: moc cuoi cua doan co tieng, can duoi "
                        "do dai file that)")

T = TypeVar("T")


async def timed(call: str, awaitable: Awaitable[T]) -> Tuple[T, int]:
    """Cho mot lan goi nha cung cap, ghi histogram `voice_provider_seconds{call}`, tra (ket qua, mili giay)."""
    started = time.perf_counter()
    try:
        return await awaitable, int((time.perf_counter() - started) * 1000)
    finally:
        PROVIDER_SECONDS.labels(call).observe(time.perf_counter() - started)


def count_request(path: str, ok: bool, error: str = "-") -> None:
    endpoint = path if path in KNOWN_ENDPOINTS else "other"  # route la: khong dung duong dan tho lam nhan
    REQUESTS.labels(endpoint, "ok" if ok else "error", "-" if ok else error).inc()


async def metrics_middleware(request: Request, call_next):
    """Dem moi request (ke ca 401 cua token). Ma loi lay tu request.state.error_code (do handler / security dat).
    Loi 500 ngoai du kien khong qua day (xem unexpected_error_handler trong api_error.py)."""
    response = await call_next(request)
    ok = response.status_code < 400
    count_request(request.url.path, ok, getattr(request.state, "error_code", f"http_{response.status_code}"))
    return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
