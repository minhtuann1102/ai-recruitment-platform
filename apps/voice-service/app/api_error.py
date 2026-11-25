"""Loi API theo contract: { error, message, details } (giong ai-service, research R8)."""
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import metrics

log = logging.getLogger("voice_service")


class ApiError(Exception):
    def __init__(self, status_code: int, error: str, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details or {}


def error_response(status_code: int, error: str, message: str, details: Optional[dict] = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message, "details": details or {}})


def register_error_handlers(app: FastAPI) -> None:
    """Moi loi toi client deu co dang { error, message, details }. Ma loi cung ghi vao request.state de
    metrics_middleware dem theo ma (xem app/metrics.py)."""

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        request.state.error_code = exc.error
        return error_response(exc.status_code, exc.error, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # contract: 400 invalid_request (ai-service tra 422). Chi gom vi tri + loai loi, khong chep gia tri nguoi dung gui
        errors = [{"loc": [str(p) for p in e["loc"]], "type": e["type"]} for e in exc.errors()]
        first = exc.errors()[0] if exc.errors() else {"loc": [], "msg": "invalid request"}
        field = ".".join(str(p) for p in first["loc"] if p != "body")
        request.state.error_code = "invalid_request"
        return error_response(400, "invalid_request", f"{field}: {first['msg']}".strip(": "), {"errors": errors})

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        # 404 / 405 va loi parse multipart cua Starlette (400): cung dang { error, message, details }
        codes = {400: "invalid_request", 404: "not_found", 405: "method_not_allowed"}
        code = codes.get(exc.status_code, "http_error")
        request.state.error_code = code
        return error_response(exc.status_code, code, str(exc.detail), {})

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        # handler nay chi ghi ten loi (thong diep ngoai le co the chua noi dung nguoi dung); Starlette van nem lai loi nay
        # nen uvicorn ghi traceback day du: khong dam bao log sach cho loi ngoai du kien. Cac duong xu ly chinh bat loi
        # va tra ApiError, khong de den day.
        log.error("unexpected_error type=%s path=%s", type(exc).__name__, request.url.path)
        # ServerErrorMiddleware nam ngoai http middleware nen metrics_middleware khong thay loi 500: dem o day
        metrics.count_request(request.url.path, ok=False, error="internal_error")
        request.state.error_code = "internal_error"
        return error_response(500, "internal_error", "Lỗi nội bộ voice-service")
