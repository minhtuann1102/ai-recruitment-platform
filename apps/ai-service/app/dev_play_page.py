"""Trang HTML tinh de dev tu phong van thu qua trinh duyet: GET /dev/play (chi khi APP_ENV khong phai staging/production).

Trang dong vai interview-service: giu plan/state/turns giua cac luot va goi /api/cv/parse, /api/jd/parse, /api/start,
/api/next-turn, /api/finalize that. Trang khong chua bi mat; API van kiem X-Internal-Token (nhap token tren trang neu
may dev co dat AI_SERVICE_INTERNAL_TOKEN).
"""
import json
import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from .api_error import ApiError
from .catalog.loader import list_tracks
from .security import STRICT_ENVS

STATIC = Path(__file__).parent / "static"
SCRIPTS = ("dev-play.js", "dev-play-api.js", "dev-play-report.js", "dev-play-trace.js")
router = APIRouter(include_in_schema=False)


def _ensure_dev() -> None:
    if os.environ.get("APP_ENV", "dev").lower() in STRICT_ENVS:
        raise ApiError(404, "not_found", "Không có trang này")


@router.get("/dev/play")
def dev_play() -> HTMLResponse:
    _ensure_dev()
    html = (STATIC / "dev-play.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace("__TRACKS__", json.dumps(list_tracks())))


@router.get("/dev/{name}")
def dev_play_script(name: str) -> Response:
    _ensure_dev()
    if name not in SCRIPTS:  # chi phuc vu file trong danh sach, khong doc duong dan tuy y
        raise ApiError(404, "not_found", "Không có file này")
    return Response((STATIC / name).read_text(encoding="utf-8"), media_type="text/javascript")
