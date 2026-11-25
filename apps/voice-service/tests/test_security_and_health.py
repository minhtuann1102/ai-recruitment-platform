"""Token noi bo, health, fail-closed o staging/production, thieu key nha cung cap (T013) va /metrics."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import TEST_TOKEN, WAV, FakeBlaze, make_settings

SUMMARY = {"turns": []}


def client_for(**overrides) -> TestClient:
    return TestClient(create_app(make_settings(**overrides), transport=FakeBlaze({}).transport))


def test_missing_or_wrong_token_is_401_and_correct_token_passes():
    client = client_for(internal_token=TEST_TOKEN)
    for headers in ({}, {"X-Internal-Token": "sai"}, {"X-Internal-Token": TEST_TOKEN + "x"}):
        r = client.post("/api/voice/session-summary", json=SUMMARY, headers=headers)
        assert r.status_code == 401
        assert r.json() == {"error": "unauthorized", "message": "Thiếu hoặc sai X-Internal-Token", "details": {}}
    ok = client.post("/api/voice/session-summary", json=SUMMARY, headers={"X-Internal-Token": TEST_TOKEN})
    assert ok.status_code == 200 and ok.json()["voice_turns"] == 0


def test_health_and_metrics_are_open_even_with_token_set():
    client = client_for(internal_token=TEST_TOKEN)
    assert client.get("/api/health").json() == {"status": "ok", "provider": "blaze"}
    assert client.get("/metrics").status_code == 200


def test_dev_without_token_does_not_check():
    assert client_for().post("/api/voice/session-summary", json=SUMMARY).status_code == 200


@pytest.mark.parametrize("env", ["staging", "production", "prod", "STAGING"])
def test_strict_env_without_token_fails_closed_but_health_stays_open(env):
    client = client_for(app_env=env)
    r = client.post("/api/voice/session-summary", json=SUMMARY)
    assert r.status_code == 503 and r.json()["error"] == "misconfigured"
    assert client.get("/api/health").status_code == 200


def test_strict_env_with_token_works():
    client = client_for(app_env="production", internal_token=TEST_TOKEN)
    assert client.post("/api/voice/session-summary", json=SUMMARY, headers={"X-Internal-Token": TEST_TOKEN}).status_code == 200


def test_missing_blaze_key_reports_unconfigured_and_provider_endpoints_return_503():
    client = client_for(blaze_api_key="")
    assert client.get("/api/health").json() == {"status": "ok", "provider": "unconfigured"}
    speak = client.post("/api/voice/speak", json={"text": "Xin chào"})
    transcribe = client.post("/api/voice/transcribe", files={"audio": ("a.wav", WAV, "audio/wav")},
                             data={"consent_confirmed": "true"})
    for r in (speak, transcribe):
        assert r.status_code == 503 and r.json()["error"] == "provider_unconfigured"
    # endpoint khong can nha cung cap van chay
    assert client.post("/api/voice/session-summary", json=SUMMARY).status_code == 200


def test_unknown_route_and_bad_method_use_error_format():
    client = client_for()
    r = client.get("/api/nope")
    assert r.status_code == 404 and set(r.json()) == {"error", "message", "details"} and r.json()["error"] == "not_found"
    assert client.get("/api/voice/speak").status_code == 405


def test_metrics_count_requests_by_endpoint_and_error_code():
    client = client_for(internal_token=TEST_TOKEN)
    client.post("/api/voice/session-summary", json=SUMMARY)  # 401
    client.post("/api/voice/session-summary", json=SUMMARY, headers={"X-Internal-Token": TEST_TOKEN})
    text = client.get("/metrics").text
    assert 'voice_requests_total{endpoint="/api/voice/session-summary",error="unauthorized",status="error"}' in text
    assert 'voice_requests_total{endpoint="/api/voice/session-summary",error="-",status="ok"}' in text
    assert "voice_provider_seconds" in text and "voice_audio_seconds_total" in text
