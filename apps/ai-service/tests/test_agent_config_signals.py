"""Thieu cau hinh LLM khong im lang: health bao that, staging/production khong khoi dong, ve mock thi co fallback."""
import asyncio
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.agents import evaluator_provider, registry
from app.agents.cv_parser import get_cv_parser
from app.agents.interviewer import get_interviewer
from app.agents.jd_parser import get_jd_parser
from app.agents.planner import get_planner
from app.agents.registry import agent_status, check_agent_config
from app.agents.reporter import get_reporter
from app.llm.errors import ConfigError
from app.llm.settings import AGENTS
from app.llm.usage import UsageCollector
from app.main import app
from app.mock_planner import load_track
from app.models_interview import CandidateState, FinalizeRequest, FinalizeTurn
from conftest import parse_sse
from test_cv_parse import CV_LINES, make_docx
from test_interview_flow import play, strong


JD_TEXT = "Tuyển lập trình viên Java backend. Yêu cầu: Spring Boot, thiết kế REST API, PostgreSQL, viết unit test. " * 2


@pytest.fixture()
def all_llm_no_key(monkeypatch):
    for agent in AGENTS:
        monkeypatch.setenv(f"AGENT_{agent.upper()}_MODE", "llm")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(registry, "_llm_agents", {})
    monkeypatch.setattr(evaluator_provider, "_llm", None)
    monkeypatch.setattr("app.llm.gateway._gateway", None)


def test_health_reports_mock_modes_and_stays_healthy(client):
    body = client.get("/api/health").json()
    assert body["status"] == "healthy" and body["agents"] == {a: "mock" for a in AGENTS}


def test_health_is_degraded_but_200_without_key(client, all_llm_no_key):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "degraded"
    assert r.json()["agents"] == {a: "config_error" for a in AGENTS}


def test_status_llm_when_key_present():
    env = {"LLM_API_KEY": "k", "AGENT_PLANNER_MODE": "llm"}
    assert agent_status(env) == {**{a: "mock" for a in AGENTS}, "planner": "llm"}


def test_health_does_not_expose_config_values(client, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-secret")
    monkeypatch.setenv("AGENT_PLANNER_MODE", "typo-value")
    assert not {"sk-secret", "typo-value"} & set(client.get("/api/health").text.split('"'))


def test_status_flags_invalid_mode_and_missing_prompt_version():
    assert agent_status({"AGENT_PLANNER_MODE": "typo"})["planner"] == "config_error"
    env = {"LLM_API_KEY": "k", "AGENT_EVALUATOR_MODE": "llm", "EVALUATOR_PROMPT_VERSION": "v999"}
    assert agent_status(env)["evaluator"] == "config_error"


@pytest.mark.parametrize("app_env", ["staging", "production", "prod"])
def test_strict_env_refuses_llm_agent_without_key(app_env):
    env = {"APP_ENV": app_env, "AGENT_EVALUATOR_MODE": "llm", "AGENT_REPORTER_MODE": "llm"}
    with pytest.raises(ConfigError, match="evaluator.*reporter|reporter.*evaluator"):
        check_agent_config(env)


def test_dev_only_logs_when_llm_agent_lacks_key(caplog):
    with caplog.at_level(logging.ERROR, logger="ai_service.agents"):
        check_agent_config({"APP_ENV": "dev", "AGENT_EVALUATOR_MODE": "llm"})
    assert "agent_config_error" in caplog.text and "evaluator" in caplog.text


def test_strict_env_warns_about_mock_agents_but_starts(caplog):
    with caplog.at_level(logging.WARNING, logger="ai_service.agents"):
        check_agent_config({"APP_ENV": "staging", "LLM_API_KEY": "k", "AGENT_PLANNER_MODE": "llm"})
    assert "agent_mock_in_strict_env" in caplog.text and "reporter" in caplog.text


def test_service_does_not_start_in_strict_env_without_key(monkeypatch, all_llm_no_key):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ConfigError):
        with TestClient(app):
            pass


def _session():
    plan, state, turns, _ = play(TestClient(app), "junior", strong)
    return FinalizeRequest(session_id="s", track="java_backend", level="junior", plan=plan, state=state,
                           end_reason="plan_complete", duration_s=1200, turns=turns)


def test_planner_records_config_fallback(all_llm_no_key):
    col = UsageCollector()
    plan = asyncio.run(get_planner().plan("java_backend", "junior", 20, None, None, col))
    assert plan.phases and col.to_metadata()["fallbacks"] == ["planner_config_error"]


def test_interviewer_records_config_fallback(all_llm_no_key):
    from app.agents.interviewer import QuestionSpec

    col = UsageCollector()
    topic = _plan().phases[1].topics[0]
    spec = QuestionSpec(action="ask_main", phase="technical", topic=topic, difficulty=2)

    async def drain():
        return "".join([tok async for tok in get_interviewer().stream(spec, col)])

    assert asyncio.run(drain()) and col.to_metadata()["fallbacks"] == ["interviewer_config_error"]


def test_reporter_without_config_is_partial_with_fallback(monkeypatch):
    req = _session()  # choi phien o che do mock truoc khi doi env
    for agent in AGENTS:
        monkeypatch.setenv(f"AGENT_{agent.upper()}_MODE", "llm")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(registry, "_llm_agents", {})
    monkeypatch.setattr("app.llm.gateway._gateway", None)
    r = TestClient(app).post("/api/finalize", json=json.loads(req.model_dump_json())).json()
    assert r["status"] == "partial" and r["meta"]["fallbacks"] == ["reporter_config_error"]


def test_unscored_stays_unscored_when_reporter_lacks_config(all_llm_no_key):
    turns = [FinalizeTurn(turn_number=1, phase="wrap_up", question="Bạn có câu hỏi nào không?", answer="Không ạ")]
    req = FinalizeRequest(session_id="s", track="java_backend", level="junior", plan=_plan(), state=CandidateState(),
                          end_reason="plan_complete", duration_s=1, turns=turns)
    col = UsageCollector()
    rep = asyncio.run(get_reporter().report(req, col))
    assert rep["status"] == "unscored" and col.to_metadata()["fallbacks"] == ["reporter_config_error"]


def _plan():
    from app.mock_planner import build_plan

    return build_plan("java_backend", "junior", 20, None, None)


def test_cv_and_jd_report_config_fallback(all_llm_no_key):
    cv = asyncio.run(get_cv_parser().parse(make_docx(CV_LINES), "java_backend"))
    assert cv.metadata.fallbacks == ["cv_parser_config_error"] and cv.metadata.model == "mock-rule-based"
    jd = asyncio.run(get_jd_parser().parse(JD_TEXT, load_track("java_backend")))
    assert jd.metadata.fallbacks == ["jd_parser_config_error"]


def test_routes_report_config_fallbacks(all_llm_no_key):
    c = TestClient(app)
    start = parse_sse(c.post("/api/start", json={"session_id": "s", "track": "java_backend", "level": "junior"}).text)
    done = start[-1][1]
    assert done["metadata"]["fallbacks"] == ["planner_config_error", "interviewer_config_error"]
    body = {"session_id": "s", "level": "junior", "track": "java_backend", "plan": done["plan"], "state": done["state"],
            "turn_number": 1, "question": done["question"], "turn_kind": done["turn"]["turn_kind"],
            "answer": "Em dùng HashMap vì tra cứu nhanh.", "elapsed_seconds": 60}
    turn = parse_sse(c.post("/api/next-turn", json=body).text)[-1][1]
    assert turn["metadata"]["fallbacks"] == ["evaluator_config_error", "interviewer_config_error"]


def test_invalid_mode_is_a_500_not_a_silent_mock(monkeypatch):
    monkeypatch.setenv("AGENT_PLANNER_MODE", "typo")  # docs 06: config_error do mode sai thi request loi, khong ve mock
    r = TestClient(app, raise_server_exceptions=False).post(
        "/api/start", json={"session_id": "s", "track": "java_backend", "level": "junior"})
    assert r.status_code == 500


def test_llm_failure_at_runtime_is_reported_and_logged(client, monkeypatch, caplog):
    from app.agents.cv_parser import LlmCvParser
    from app.agents.jd_parser import LlmJdParser
    from app.llm.gateway import LlmGateway
    from app.llm.settings import load_llm_settings
    from fakes.fake_llm import FakeOpenAI, status_error

    async def no_sleep(_):
        return None

    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), FakeOpenAI([status_error(500)] * 8), env={},
                    sleep=no_sleep, rng=lambda: 0.0)
    monkeypatch.setattr("app.main.get_cv_parser", lambda: LlmCvParser(gw))
    monkeypatch.setattr("app.main.get_jd_parser", lambda: LlmJdParser(gw))
    with caplog.at_level(logging.INFO, logger="ai_service"):
        cv = client.post("/api/cv/parse", files={"file": ("cv.docx", make_docx(CV_LINES))},
                         data={"track": "java_backend"})
        jd = client.post("/api/jd/parse", json={"track": "java_backend", "jd_text": JD_TEXT})
    assert cv.json()["metadata"]["fallbacks"] == ["cv_parser_fallback"]
    assert jd.json()["metadata"]["fallbacks"] == ["jd_parser_fallback"]
    assert "fallbacks=cv_parser_fallback" in caplog.text and "fallbacks=jd_parser_fallback" in caplog.text


def test_mock_mode_has_no_fallback(client):
    assert asyncio.run(get_cv_parser().parse(make_docx(CV_LINES), "java_backend")).metadata.fallbacks == []
