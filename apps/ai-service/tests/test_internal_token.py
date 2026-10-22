"""X-Internal-Token (FR-AI-091): khong token -> 401, sai token -> 401, health luon mo; chua cau hinh thi mo (dev)."""
import pytest


@pytest.fixture()
def secured(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")


def test_missing_or_wrong_token_rejected(client, secured):
    body = {"session_id": "s", "track": "java_backend", "level": "junior"}
    r = client.post("/api/start", json=body)
    assert r.status_code == 401 and r.json()["error"] == "unauthorized"
    assert client.post("/api/start", json=body, headers={"X-Internal-Token": "wrong"}).status_code == 401
    assert client.post("/api/jd/parse", json={}).status_code == 401  # kiem token truoc validate body
    assert client.get("/openapi.json").status_code == 401


def test_valid_token_and_health_open(client, secured):
    ok = client.post("/api/start", json={"session_id": "s", "track": "java_backend", "level": "junior"},
                     headers={"X-Internal-Token": "s3cret-token"})
    assert ok.status_code == 200
    assert client.get("/api/health").status_code == 200


def test_unconfigured_token_allows_requests_for_dev(client, monkeypatch):
    monkeypatch.delenv("AI_SERVICE_INTERNAL_TOKEN", raising=False)
    assert client.post("/api/start", json={"session_id": "s", "track": "java_backend",
                                           "level": "junior"}).status_code == 200


def test_strict_env_without_token_fails_closed(client, monkeypatch):
    monkeypatch.delenv("AI_SERVICE_INTERNAL_TOKEN", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    r = client.post("/api/start", json={"session_id": "s", "track": "java_backend", "level": "junior"})
    assert r.status_code == 503 and r.json()["error"] == "misconfigured"
    assert client.get("/api/health").status_code == 200
