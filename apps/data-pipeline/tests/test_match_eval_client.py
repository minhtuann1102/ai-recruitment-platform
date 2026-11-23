"""T031 phu (spec 017 US3): client httpx goi POST /api/match/jobs (httpx.MockTransport, khong mang) + cau hinh env.

Header X-Internal-Token chi gui khi co token (ai-service dev khong dat token thi bo qua kiem tra). Moi loi ket noi,
HTTP khac 200, JSON hong hay response sai hinh deu thanh AiServiceError (ma thoat 2 cua lenh).
"""
import json

import httpx
import pytest

from pipeline.match_eval_client import AiServiceError, MatchClient, build_request
from pipeline.settings import ConfigError, MatchEvalSettings, require_match_eval_settings

GOOD = {"items": [{"job_id": "x:1", "score": 0.5, "components": {"cosine": 0.4, "skill_match": 0.6, "level_fit": 1.0}}],
        "page": 1, "page_size": 50, "total": 1, "metadata": {"degraded": False, "mock": False, "timing_ms": {"score": 3}}}


def client(handler, token="tok", url="http://svc"):
    return MatchClient(MatchEvalSettings(url, token, 0.02), transport=httpx.MockTransport(handler))


def test_posts_json_with_internal_token_and_returns_body_and_client_time():
    seen = {}

    def handler(request):
        seen.update(method=request.method, path=request.url.path, token=request.headers.get("X-Internal-Token"),
                    body=json.loads(request.content))
        return httpx.Response(200, json=GOOD)

    reply = client(handler, url="http://svc/").match({"track": "java_backend", "page_size": 50})  # dau / cuoi URL duoc bo
    assert seen == {"method": "POST", "path": "/api/match/jobs", "token": "tok", "body": {"track": "java_backend", "page_size": 50}}
    assert reply.body == GOOD and reply.client_ms >= 0


def test_header_is_omitted_when_no_token():
    headers = {}
    client(lambda r: headers.update(r.headers) or httpx.Response(200, json=GOOD), token="").match({})
    assert "x-internal-token" not in headers


@pytest.mark.parametrize("response, fragment", [
    (httpx.Response(401, json={"error": "unauthorized", "message": "sai token", "details": None}), "401"),
    (httpx.Response(422, json={"error": "unknown_track", "message": "track la", "details": None}), "unknown_track"),
    (httpx.Response(503, json={"error": "match_index_unavailable", "message": "chua co", "details": None}), "match_index_unavailable"),
    (httpx.Response(500, text="boom"), "500"),
    (httpx.Response(200, text="not json"), "JSON"),
    (httpx.Response(200, json={"items": []}), "metadata"),
    (httpx.Response(200, json={"metadata": {}}), "items"),
    (httpx.Response(200, json={**GOOD, "items": [{"job_id": "x:1", "score": 0.5}]}), "components"),
    (httpx.Response(200, json={**GOOD, "items": [{"job_id": "x:1", "score": "0.5", "components": GOOD["items"][0]["components"]}]}), "score"),
])
def test_bad_replies_become_ai_service_error(response, fragment):
    with pytest.raises(AiServiceError) as err:
        client(lambda r: response).match({})
    assert fragment in str(err.value)


@pytest.mark.parametrize("exc", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")])
def test_network_errors_become_ai_service_error_naming_the_url(exc):
    def handler(request):
        raise exc

    with pytest.raises(AiServiceError, match="http://svc"):
        client(handler).match({})


def test_build_request_matches_contract_and_omits_job_ids_when_none():
    cv = {"cv_id": "cv-a", "track": "java_backend", "level": "junior", "note": "n", "cv_profile": {"headline": "cv-a"}}
    with_ids = build_request(cv, "2026-11-01", ["x:1"], 50)
    assert with_ids == {"cv_profile": {"headline": "cv-a"}, "track": "java_backend", "level": "junior", "as_of": "2026-11-01",
                        "job_ids": ["x:1"], "page": 1, "page_size": 50}
    assert "job_ids" not in build_request(cv, "2026-11-01", None, 10)


# ---- cau hinh ----
def test_settings_defaults_and_overrides(monkeypatch):
    for name in ("AI_SERVICE_URL", "AI_SERVICE_INTERNAL_TOKEN", "EMBEDDING_PRICE_PER_1M"):
        monkeypatch.delenv(name, raising=False)
    assert require_match_eval_settings() == MatchEvalSettings("http://localhost:8000", "", 0.02)
    monkeypatch.setenv("AI_SERVICE_URL", "http://ai:9000/")
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", " secret ")
    monkeypatch.setenv("EMBEDDING_PRICE_PER_1M", "0.13")
    assert require_match_eval_settings() == MatchEvalSettings("http://ai:9000", "secret", 0.13)


@pytest.mark.parametrize("price", ["abc", "-1", "nan"])
def test_invalid_price_is_a_config_error(monkeypatch, price):
    monkeypatch.setenv("EMBEDDING_PRICE_PER_1M", price)
    with pytest.raises(ConfigError, match="EMBEDDING_PRICE_PER_1M"):
        require_match_eval_settings()
