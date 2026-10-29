"""metadata.rag: RAG bat mac dinh; cau hinh sai hay ai_db loi thi phien chay khong co RAG va response bao loi."""
import app.plan_snippets as ps
from app.llm.usage import UsageCollector
from app.main import app
from app.rag.circuit_breaker import CircuitBreaker
from fastapi.testclient import TestClient


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def _set(monkeypatch, retriever=None, config_error=None, breaker=None):
    monkeypatch.setattr(ps, "_loaded", True)
    monkeypatch.setattr(ps, "_retriever", retriever)
    monkeypatch.setattr(ps, "_config_error", config_error)
    monkeypatch.setattr(ps, "_breaker", breaker or CircuitBreaker(60))


def test_status_off_when_disabled(monkeypatch):
    _set(monkeypatch)
    assert ps.rag_status(UsageCollector()) == {"status": "off"}


def test_status_on_and_runtime_error(monkeypatch):
    _set(monkeypatch, retriever=object())
    collector = UsageCollector()
    assert ps.rag_status(collector) == {"status": "on"}
    collector.rag_error("rag_bank_failed")
    collector.rag_error("rag_bank_failed")  # khong lap ma loi
    assert ps.rag_status(collector) == {"status": "error", "errors": ["rag_bank_failed"],
                                        "message": ps.RAG_ERROR_MESSAGE}


def test_status_config_error_turns_rag_off(monkeypatch):
    _set(monkeypatch, config_error="AI_DB_URL chua duoc dat")
    status = ps.rag_status(UsageCollector())
    assert status["status"] == "error" and status["errors"] == ["rag_config_error"]
    assert "AI_DB_URL" in status["message"]


def test_get_retriever_records_config_error(monkeypatch):
    monkeypatch.setattr(ps, "_loaded", False)
    monkeypatch.setattr(ps, "_retriever", None)
    monkeypatch.setattr(ps, "_config_error", None)
    monkeypatch.setattr(ps, "_breaker", CircuitBreaker(60))
    monkeypatch.delenv("RAG_ENABLED")  # mac dinh bat
    monkeypatch.delenv("AI_DB_URL", raising=False)
    assert ps.get_retriever() is None and ps.rag_status()["errors"] == ["rag_config_error"]


def _done(body: str) -> str:
    return body.split("event: done", 1)[1]


def test_start_reports_rag_error_in_metadata_and_session_runs(monkeypatch):
    _set(monkeypatch, config_error="AI_DB_URL chua duoc dat")
    r = TestClient(app).post("/api/start", json={"session_id": "s", "track": "java_backend", "level": "junior",
                                                 "duration_minutes": 20})
    assert r.status_code == 200 and '"question"' in _done(r.text)
    assert '"rag": {"status": "error"' in _done(r.text) and '"rag_unavailable"' in _done(r.text)


def test_breaker_skips_rag_after_error_then_retries(monkeypatch):
    clock, retriever = Clock(), object()
    _set(monkeypatch, retriever=retriever, breaker=CircuitBreaker(60, clock))
    collector = UsageCollector()
    collector.rag_error("rag_timeout")
    ps.note_rag_errors(collector)
    assert ps.get_retriever() is None  # dang ngat: request sau khong cho ai_db
    status = ps.rag_status(UsageCollector())
    assert status["errors"] == ["rag_cooldown"] and status["last_errors"] == ["rag_timeout"]
    assert "60 s" in status["message"]
    clock.now += 61
    assert ps.get_retriever() is retriever and ps.rag_status(UsageCollector()) == {"status": "on"}


def test_breaker_disabled_with_zero_cooldown(monkeypatch):
    _set(monkeypatch, retriever=object(), breaker=CircuitBreaker(0))
    collector = UsageCollector()
    collector.rag_error("rag_bank_failed")
    ps.note_rag_errors(collector)
    assert ps.get_retriever() is not None


def test_health_reports_rag_status_and_stays_healthy(monkeypatch):
    _set(monkeypatch, config_error="AI_DB_URL chua duoc dat")
    body = TestClient(app).get("/api/health").json()
    assert body["status"] == "healthy" and body["rag"]["status"] == "error"
    _set(monkeypatch)
    assert TestClient(app).get("/api/health").json()["rag"] == {"status": "off"}
