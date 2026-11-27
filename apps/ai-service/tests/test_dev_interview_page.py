"""Trang dev /dev/interview va proxy /dev/voice/*: chi mo o dev, trang khong qua token, proxy van can token
(goi Blaze ton phi), chi phuc vu file trong danh sach, chuyen tiep nguyen byte / ma loi cua voice-service."""
import re

import httpx
import pytest

from app import dev_voice_proxy
from app.catalog.loader import list_tracks
from app.dev_interview_page import FILES

REAL_ASYNC_CLIENT = httpx.AsyncClient  # giu ban goc: mot test co the thay voice-service hai lan


@pytest.fixture(autouse=True)
def _no_tokens(monkeypatch):  # .env cua may dev co the dat token: test tu dat khi can
    for name in ("AI_SERVICE_INTERNAL_TOKEN", "VOICE_SERVICE_INTERNAL_TOKEN", "APP_ENV"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("VOICE_SERVICE_URL", "http://voice.test")


def _fake_voice_service(monkeypatch, handler):
    """Thay voice-service bang httpx.MockTransport; tra danh sach request da nhan de kiem."""
    seen = []

    def record(request: httpx.Request):
        seen.append(request)
        return handler(request)

    monkeypatch.setattr(dev_voice_proxy.httpx, "AsyncClient",
                        lambda **kw: REAL_ASYNC_CLIENT(transport=httpx.MockTransport(record), **kw))
    return seen


def test_page_lists_tracks_and_every_referenced_file_is_served(client):
    r = client.get("/dev/interview")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "__TRACKS__" not in r.text and f'"{list_tracks()[0]}"' in r.text
    referenced = set(re.findall(r'/dev/interview/([\w./-]+)', r.text))
    assert referenced and referenced <= set(FILES)
    for name, media in FILES.items():
        f = client.get(f"/dev/interview/{name}")
        assert f.status_code == 200 and f.headers["content-type"].startswith(media) and f.content
    for shared in re.findall(r'src="(/dev/dev-play-[\w-]+\.js)"', r.text):  # file dung chung voi /dev/play
        assert client.get(shared).status_code == 200


def test_page_open_without_token_but_voice_proxy_protected(client, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")
    seen = _fake_voice_service(monkeypatch, lambda req: httpx.Response(200, json={"status": "ok", "provider": "blaze"}))
    assert client.get("/dev/interview").status_code == 200
    assert client.get("/dev/interview/interview-app.js").status_code == 200
    assert client.post("/dev/voice/speak", json={"text": "x"}).status_code == 401
    assert client.get("/dev/voice/health").status_code == 401
    assert client.get("/dev/voice/health", headers={"X-Internal-Token": "s3cret-token"}).status_code == 200
    assert len(seen) == 1


def test_hidden_in_strict_env(client, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")
    monkeypatch.setenv("APP_ENV", "production")
    seen = _fake_voice_service(monkeypatch, lambda req: httpx.Response(200, json={}))
    auth = {"X-Internal-Token": "s3cret-token"}
    assert client.get("/dev/interview").status_code == 404
    assert client.get("/dev/interview/interview.css").status_code == 404
    assert client.get("/dev/voice/health", headers=auth).status_code == 404
    assert client.post("/dev/voice/session-summary", json={"turns": []}, headers=auth).status_code == 404
    assert seen == []


def test_only_listed_files_served(client):
    assert client.get("/dev/interview/assets/nope.svg").status_code == 404
    assert client.get("/dev/interview/interview.html").status_code == 404  # trang chi qua /dev/interview (thay TRACKS)
    assert client.get("/dev/interview/..%2F..%2Fmain.py").status_code == 404


def test_transcribe_forwards_bytes_with_length_and_server_token(client, monkeypatch):
    monkeypatch.setenv("VOICE_SERVICE_INTERNAL_TOKEN", "voice-token")
    body = {"no_speech": False, "transcript": "dạ HashMap", "segments": [], "metrics": None, "warnings": [], "provider": {}}
    seen = _fake_voice_service(monkeypatch, lambda req: httpx.Response(200, json=body))
    r = client.post("/dev/voice/transcribe", files={"audio": ("a.webm", b"\x1aE\xdf\xa3" * 100, "audio/webm")},
                    data={"consent_confirmed": "true", "keywords": ["HashMap", "JVM"]})
    assert r.status_code == 200 and r.json() == body
    req = seen[0]
    assert str(req.url) == "http://voice.test/api/voice/transcribe"
    assert req.headers["x-internal-token"] == "voice-token"
    assert req.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert int(req.headers["content-length"]) == len(req.content) and b"\x1aE\xdf\xa3" in req.content
    assert "transfer-encoding" not in req.headers


def test_transcribe_passes_voice_service_errors_through(client, monkeypatch):
    err = {"error": "consent_required", "message": "Cần đồng ý", "details": {}}
    _fake_voice_service(monkeypatch, lambda req: httpx.Response(400, json=err))
    r = client.post("/dev/voice/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert r.status_code == 400 and r.json() == err


def test_transcribe_rejects_oversized_body_before_forwarding(client, monkeypatch):
    seen = _fake_voice_service(monkeypatch, lambda req: httpx.Response(200, json={}))
    monkeypatch.setattr(dev_voice_proxy, "MAX_BODY_BYTES", 100)
    r = client.post("/dev/voice/transcribe", files={"audio": ("a.webm", b"x" * 500, "audio/webm")})
    assert r.status_code == 413 and r.json()["error"] == "audio_too_long" and seen == []


def test_speak_streams_audio_and_passes_errors(client, monkeypatch):
    mp3 = b"ID3" + b"\x00" * 2000
    _fake_voice_service(monkeypatch, lambda req: httpx.Response(200, content=mp3, headers={"content-type": "audio/mpeg"}))
    r = client.post("/dev/voice/speak", json={"text": "Câu hỏi?"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg" and r.content == mp3

    err = {"error": "provider_unconfigured", "message": "Thiếu khoá", "details": {}}
    _fake_voice_service(monkeypatch, lambda req: httpx.Response(503, json=err))
    r = client.post("/dev/voice/speak", json={"text": "Câu hỏi?"})
    assert r.status_code == 503 and r.json() == err


def test_session_summary_forwards_json(client, monkeypatch):
    seen = _fake_voice_service(monkeypatch, lambda req: httpx.Response(200, json={"voice_turns": 0, "stats": {},
                                                                                  "counts": {}, "notes": []}))
    r = client.post("/dev/voice/session-summary", json={"turns": []})
    assert r.status_code == 200 and r.json()["voice_turns"] == 0
    assert seen[0].headers["content-type"] == "application/json" and seen[0].content == b'{"turns":[]}'
    assert "x-internal-token" not in seen[0].headers  # may dev chua dat token cho voice-service: khong gui


def test_unreachable_voice_service_is_502(client, monkeypatch):
    def down(req):
        raise httpx.ConnectError("refused", request=req)
    _fake_voice_service(monkeypatch, down)
    for r in (client.get("/dev/voice/health"), client.post("/dev/voice/speak", json={"text": "x"})):
        assert r.status_code == 502 and r.json()["error"] == "voice_service_unreachable"


def test_proxy_rejects_cross_site_and_non_json_before_calling_upstream(client, monkeypatch):
    seen = _fake_voice_service(monkeypatch, lambda req: httpx.Response(200, json={}))
    r = client.post("/dev/voice/speak", json={"text": "x"}, headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403
    r = client.post("/dev/voice/speak", content=b'{"text":"x"}', headers={"Content-Type": "text/plain"})
    assert r.status_code == 415  # POST text/plain lien site khong can preflight: bat buoc JSON
    assert client.post("/dev/voice/session-summary", json={"turns": []},
                       headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200
    assert len(seen) == 1


def test_timeout_is_504_not_unreachable(client, monkeypatch):
    def slow(req):
        raise httpx.ReadTimeout("slow", request=req)
    _fake_voice_service(monkeypatch, slow)
    r = client.post("/dev/voice/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert r.status_code == 504 and r.json()["error"] == "voice_service_timeout"


def test_only_static_file_paths_skip_token(client, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")
    assert client.get("/dev/interview/assets/star-decoration.svg").status_code == 200
    assert client.get("/dev/interview/some-future-route").status_code == 401  # khong phai file tinh: van can token
