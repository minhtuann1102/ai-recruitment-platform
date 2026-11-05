"""So lieu Prometheus (app/metrics.py, GET /metrics): dem dung mot lan moi request, nhan chi la ma, /metrics can token.
Registry dung chung giua cac test nen kiem do chenh truoc / sau."""
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.llm.usage import CallRecord, UsageCollector
from app.main import app
from app.metrics import record_request
from conftest import parse_sse


def value(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0


SID = "sess-metrics-x"


def ttft_count():
    return sum(value("ai_ttft_seconds_count", endpoint="next_turn", source=s) for s in ("ai", "fallback"))


def start(client, sid=SID):
    r = client.post("/api/start", json={"session_id": sid, "track": "java_backend", "level": "junior"})
    return parse_sse(r.text)[-1][1]


def turn(done, **over):
    return {"session_id": SID, "level": "junior", "track": "java_backend", "plan": done["plan"],
            "state": done["state"], "turn_number": 1, "question": done["question"],
            "answer": "Em dùng HashMap và ConcurrentHashMap khi nhiều thread", "elapsed_seconds": 60, **over}


def test_turn_requests_are_counted_once_with_ttft_and_outcome(client):
    before = (value("ai_requests_total", endpoint="start", status="ok", error="-"),
              ttft_count(),
              value("ai_turns_total", answer_source="text", outcome="answered"),
              value("ai_http_responses_total", route="/api/next-turn", code="200"))
    done = start(client)
    client.post("/api/next-turn", json=turn(done))
    after = (value("ai_requests_total", endpoint="start", status="ok", error="-"),
             ttft_count(),
             value("ai_turns_total", answer_source="text", outcome="answered"),
             value("ai_http_responses_total", route="/api/next-turn", code="200"))
    assert [a - b for a, b in zip(after, before)] == [1, 1, 1, 1]
    assert value("ai_request_duration_seconds_count", endpoint="next_turn") >= 1


def test_api_errors_are_labelled_by_code(client):
    done = start(client)
    key = {"endpoint": "next_turn", "status": "error", "error": "voice_no_speech"}
    before = value("ai_requests_total", **key)
    assert client.post("/api/next-turn", json=turn(done, answer="ừm", answer_source="voice")).status_code == 422
    assert value("ai_requests_total", **key) - before == 1


def test_agent_calls_tokens_and_rag_errors():
    col = UsageCollector()
    col.add(CallRecord("evaluator", "m", input_tokens=100, output_tokens=20, cached_tokens=64, latency_ms=900))
    col.add(CallRecord("interviewer", "fallback", fallback="interviewer_fallback"))
    col.rag_error("rag_timeout")
    keys = [("ai_agent_calls_total", {"agent": "evaluator", "fallback": "none"}),
            ("ai_agent_calls_total", {"agent": "interviewer", "fallback": "interviewer_fallback"}),
            ("ai_tokens_total", {"agent": "evaluator", "kind": "input"}),
            ("ai_tokens_total", {"agent": "evaluator", "kind": "cached"}),
            ("ai_agent_latency_seconds_count", {"agent": "evaluator"}),
            ("ai_rag_errors_total", {"code": "rag_timeout"}),
            ("ai_rag_requests_total", {"status": "partial"})]
    before = [value(n, **lb) for n, lb in keys]
    record_request("next_turn", "ok", "-", 1.2, col, "partial")
    record_request("finalize", "ok", "-", 0.5, UsageCollector(), "-")  # khong dung RAG: khong dem
    assert [value(n, **lb) - b for (n, lb), b in zip(keys, before)] == [1, 1, 100, 64, 1, 1, 1]


def test_metrics_endpoint_needs_token_and_uses_route_templates(client, monkeypatch):
    client.get("/dev/khong-co")  # duong dan la: nhan theo mau route, khong theo duong dan that
    client.get("/khong-co-route")
    body = client.get("/metrics").text
    assert 'route="/dev/{name}"' in body and 'route="other"' in body and "khong-co" not in body
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")
    before = value("ai_http_responses_total", route="/metrics", code="401")
    assert client.get("/metrics").status_code == 401
    assert value("ai_http_responses_total", route="/metrics", code="401") - before == 1  # dem ca request bi chan
    ok = client.get("/metrics", headers={"X-Internal-Token": "s3cret-token"})
    assert ok.status_code == 200 and ok.headers["content-type"].startswith("text/plain")
    assert "ai_requests_total" in ok.text and "_created" not in ok.text
    assert SID not in ok.text and "java_backend" not in ok.text  # khong co session_id, track lam nhan


def test_unhandled_error_is_counted_as_500(monkeypatch):
    class Broken:
        async def parse(self, *_):
            raise RuntimeError("boom")
    monkeypatch.setattr("app.main.get_jd_parser", lambda: Broken())
    keys = [("ai_http_responses_total", {"route": "/api/jd/parse", "code": "500"}),
            ("ai_requests_total", {"endpoint": "jd_parse", "status": "error", "error": "RuntimeError"})]
    before = [value(n, **lb) for n, lb in keys]
    r = TestClient(app, raise_server_exceptions=False).post(
        "/api/jd/parse", json={"track": "java_backend", "jd_text": "Backend Java, Spring Boot, Kafka. " * 3})
    assert r.status_code == 500
    assert [value(n, **lb) - b for (n, lb), b in zip(keys, before)] == [1, 1]
