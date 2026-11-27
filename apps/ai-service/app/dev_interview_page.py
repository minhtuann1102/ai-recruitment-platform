"""Man phong van bang giong noi cho ung vien, GET /dev/interview (chi khi APP_ENV dev; ban that do web cua FSD).

Giao dien theo file Figma cong dong "AI Video Interview App" (cac man Fill the Basic Details, Permission, Audio
Question, Result), viet cho nguoi dung cuoi (khong bang debug). Trang dong vai interview-service: giu plan/state/turns,
goi /api/start, /api/next-turn, /api/finalize; giong noi di qua proxy /dev/voice/* (app/dev_voice_proxy.py).
Trang khong chua bi mat.
"""
import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from .api_error import ApiError
from .catalog.loader import list_tracks, load_catalog
from .dev_play_page import ensure_dev

ROOT = Path(__file__).parent / "static" / "interview"
# chi phuc vu file trong danh sach (khong doc duong dan tuy y); key = ten tren URL, value = media type
FILES = {
    "interview.css": "text/css",
    "interview-api.js": "text/javascript",
    "interview-app.js": "text/javascript",
    "interview-chat.js": "text/javascript",
    "interview-report.js": "text/javascript",
    "interview-turn.js": "text/javascript",
    "interview-voice.js": "text/javascript",
    "interview-result.js": "text/javascript",
    **{f"assets/{p.name}": "image/svg+xml" for p in (ROOT / "assets").glob("*.svg")},
}
router = APIRouter(include_in_schema=False)


@router.get("/dev/interview")
def dev_interview() -> HTMLResponse:
    ensure_dev()
    html = (ROOT / "interview.html").read_text(encoding="utf-8")
    tracks = [{"id": t, "title": load_catalog(t).title} for t in list_tracks()]  # ten vi tri hien cho ung vien
    data = json.dumps(tracks, ensure_ascii=False).replace("<", "\\u003c")  # nam trong <script>: chan "</script>"
    return HTMLResponse(html.replace("__TRACKS__", data))


@router.get("/dev/interview/{name:path}")
def dev_interview_file(name: str) -> Response:
    ensure_dev()
    if name not in FILES:
        raise ApiError(404, "not_found", "Không có file này")
    return Response((ROOT / name).read_bytes(), media_type=FILES[name])
