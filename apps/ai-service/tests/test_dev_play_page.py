"""Trang dev /dev/play: chi mo o dev, khong qua token (khong chua bi mat), chi phuc vu file trong danh sach."""
from app.catalog.loader import list_tracks
from app.dev_play_page import SCRIPTS
from app.security import DEV_PAGE_PATHS


def test_page_lists_tracks_and_scripts_load(client):
    r = client.get("/dev/play")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "__TRACKS__" not in r.text and f'"{list_tracks()[0]}"' in r.text
    for name in SCRIPTS:
        js = client.get(f"/dev/{name}")
        assert js.status_code == 200 and js.headers["content-type"].startswith("text/javascript")


def test_page_open_without_token_but_api_still_protected(client, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")
    assert client.get("/dev/play").status_code == 200
    assert client.post("/api/start", json={"session_id": "s", "track": "java_backend",
                                           "level": "junior"}).status_code == 401
    assert {"/dev/play", *(f"/dev/{n}" for n in SCRIPTS)} == DEV_PAGE_PATHS


def test_hidden_in_strict_env(client, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")
    monkeypatch.setenv("APP_ENV", "production")
    assert client.get("/dev/play").status_code == 404
    assert client.get("/dev/dev-play.js").status_code == 404


def test_only_listed_files_served(client):
    assert client.get("/dev/dev_play_page.py").status_code == 404
    assert client.get("/dev/..%2Fmain.py").status_code == 404
