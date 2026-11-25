"""voice-service: STT / TTS qua Blaze + chi so trinh bay, stateless, noi bo (spec 015).

Contract: specs/015-voice-mode/contracts/voice-service-api.md. `create_app` nhan Settings va transport httpx de test thay
bang httpx.MockTransport (khong mang, khong key); `app` o cuoi file la ban chay that cho uvicorn (`app.main:app`).
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI

from . import metrics
from .api_error import register_error_handlers
from .audio_validation import keep_uploads_in_memory
from .blaze_client import BlazeClient
from .config import Settings, load_settings
from .openapi_docs import build_openapi
from .security import internal_token_middleware
from .speak_route import router as speak_router
from .summary_route import router as summary_router
from .transcribe_route import router as transcribe_router

log = logging.getLogger("voice_service")


def _configure_logging() -> None:
    """uvicorn khong cau hinh logger cua app: neu chua co handler thi bat INFO. httpx ghi moi request o muc INFO nen ha xuong."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(),
                            format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app(settings: Optional[Settings] = None, transport: Optional[httpx.AsyncBaseTransport] = None) -> FastAPI:
    settings = settings or load_settings()
    # thieu BLAZE_API_KEY: service van len, /api/health bao unconfigured, endpoint giong tra 503 provider_unconfigured
    blaze = BlazeClient(settings, transport) if settings.blaze_api_key else None
    if blaze is None:
        log.warning("provider_unconfigured BLAZE_API_KEY chua dat: endpoint giong se tra 503")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if blaze is not None:
            await blaze.aclose()

    app = FastAPI(title="Voice Service (Blaze STT/TTS)", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.blaze = blaze
    keep_uploads_in_memory(settings.max_upload_bytes)
    register_error_handlers(app)
    app.middleware("http")(internal_token_middleware)
    app.middleware("http")(metrics.metrics_middleware)  # dang ky sau = boc ngoai: dem ca 401 cua token
    app.include_router(transcribe_router)
    app.include_router(speak_router)
    app.include_router(summary_router)
    app.openapi = lambda: build_openapi(app)  # Swagger khop hanh vi: bo 422, co body loi (openapi_docs.py)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "provider": "blaze" if app.state.blaze is not None else "unconfigured"}

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics():
        return metrics.metrics_response()

    return app


_configure_logging()
app = create_app()
