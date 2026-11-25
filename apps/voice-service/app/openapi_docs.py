"""Mo ta loi trong OpenAPI (Swagger) cho ca 3 endpoint, dung ma loi cua contract voice-service-api.md.

Moi loi co body { error, message, details } (ErrorBody). FastAPI tu them response 422 cho endpoint co body, nhung service
tra 400 invalid_request: build_openapi go 422 va schema HTTPValidationError di de Swagger khop hanh vi.
"""
from typing import Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel


class ErrorBody(BaseModel):
    error: str
    message: str
    details: dict = {}


# {ma HTTP: "ma1 | ma2"} theo tung endpoint (contract muc "Loi")
AUTH_ERRORS = {401: "unauthorized (thiếu hoặc sai X-Internal-Token)",
               503: "misconfigured (staging/production thiếu token nội bộ)"}
TRANSCRIBE_ERRORS = {
    400: "consent_required | invalid_request", 401: AUTH_ERRORS[401], 402: "quota_exceeded", 411: "length_required",
    413: "audio_too_long", 415: "invalid_audio", 429: "provider_rate_limited", 502: "provider_error",
    503: "provider_unconfigured | misconfigured", 504: "provider_timeout"}
SPEAK_ERRORS = {
    400: "text_too_long | invalid_voice | invalid_request", 401: AUTH_ERRORS[401], 402: "quota_exceeded",
    429: "provider_rate_limited", 502: "provider_error", 503: "provider_unconfigured | misconfigured",
    504: "provider_timeout"}
SUMMARY_ERRORS = {400: "invalid_request", **AUTH_ERRORS}


def error_responses(codes: Dict[int, str]) -> Dict[int, dict]:
    """Tham so `responses=` cua FastAPI: moi ma HTTP co body ErrorBody va danh sach ma loi."""
    return {status: {"model": ErrorBody, "description": text} for status, text in codes.items()}


def build_openapi(app: FastAPI) -> dict:
    if app.openapi_schema is None:
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for path_item in schema["paths"].values():
            for operation in path_item.values():
                operation.get("responses", {}).pop("422", None)
        for name in ("HTTPValidationError", "ValidationError"):
            schema.get("components", {}).get("schemas", {}).pop(name, None)
        app.openapi_schema = schema
    return app.openapi_schema
