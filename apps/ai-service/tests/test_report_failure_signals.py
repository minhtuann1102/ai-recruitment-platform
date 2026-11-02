"""Bao cao khi luong AI hong: khong cham duoc, Reporter loi, prompt_versions that, thieu dap an chuan."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from test_interview_flow import play, strong
from test_reporter import make, output

from app.agents.evaluator import LlmEvaluator
from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from app.models_interview import FinalizeRequest, FinalizeTurn
from app.report_scoring import build_report
from fakes.fake_llm import FakeOpenAI, status_error


@pytest.fixture(scope="module")
def session():
    from fastapi.testclient import TestClient
    from app.main import app

    plan, state, turns, _ = play(TestClient(app), "junior", strong)
    return FinalizeRequest(session_id="s", track="java_backend", level="junior", plan=plan, state=state,
                           end_reason="plan_complete", duration_s=1200, turns=turns)


def with_evals(req: FinalizeRequest, pick=lambda t: True, **update) -> FinalizeRequest:
    """Ban sao cua req voi cac truong Evaluation doi o nhung luot duoc chon."""
    turns = [t.model_copy(update={"evaluation": t.evaluation.model_copy(update=update)})
             if t.evaluation and pick(t) else t for t in req.turns]
    return req.model_copy(update={"turns": turns})


@pytest.mark.parametrize("update", [{"degraded": True}, {"answer_type": "asks_clarification"}])
def test_nothing_scored_has_no_score_or_verdict(session, update):
    rep = build_report(with_evals(session, **update))
    assert rep["status"] == "unscored"
    assert rep["overall"]["score"] is None and rep["overall"]["verdict"] is None
    assert set(rep["criteria"].values()) == {None}
    assert rep["sections"] == [] and rep["session"]["evaluated_turns"] == 0 and rep["session"]["confidence"] == "low"
    assert "chưa có điểm" in rep["overall"]["summary"].lower()


def test_session_ended_before_any_answer_is_unscored(session):
    only_wrap_up = [FinalizeTurn(turn_number=1, phase="wrap_up", question="Còn câu hỏi không?", answer="Không ạ")]
    assert build_report(session.model_copy(update={"turns": only_wrap_up}))["status"] == "unscored"


def test_scored_turns_without_a_plan_topic_are_unscored_not_zero(session):
    rep = build_report(session.model_copy(update={"turns": [t.model_copy(update={"topic_id": None})
                                                            for t in session.turns]}))
    assert rep["status"] == "unscored" and rep["overall"]["score"] is None and rep["sections"] == []


def test_all_dont_know_is_a_real_zero(session):
    rep = build_report(with_evals(session, answer_type="dont_know", turn_score_10=0.0))
    assert rep["status"] == "complete" and rep["overall"]["score"] == 0.0 and rep["overall"]["verdict"] == "below"


def test_one_scored_turn_keeps_a_score(session):
    last = max(t.turn_number for t in session.turns if t.phase != "wrap_up")
    rep = build_report(with_evals(session, lambda t: t.turn_number != last, degraded=True))
    assert rep["status"] == "complete" and rep["overall"]["score"] is not None
    assert rep["session"]["confidence"] == "low"


def test_eval_metrics_leave_out_unscored_sessions():
    from evals.sim_metrics import discrimination, injection

    persona = lambda q, b=(), base=None: SimpleNamespace(level="junior", track="java", quality=q, behaviors=b,  # noqa: E731
                                                         base_id=base)
    sess = lambda score, verdict="below": {"report": {"overall": {"score": score, "verdict": verdict}}}  # noqa: E731
    personas = {"s": persona("strong"), "a": persona("average"), "w": persona("weak"),
                "i": persona("average", ("injection_attempt",), "a")}
    sessions = {"s": sess(None, None), "a": sess(5.0), "w": sess(2.0), "i": sess(None, None)}
    assert injection(sessions, personas)["pairs"] == 0  # phien hong khong duoc tinh la "khong tang diem"
    assert discrimination(sessions, personas)["groups"] == 0


def test_finalize_route_returns_unscored_as_200(client, session):
    body = json.loads(with_evals(session, degraded=True).model_dump_json())
    r = client.post("/api/finalize", json=body)
    assert r.status_code == 200 and r.json()["status"] == "unscored" and r.json()["overall"]["score"] is None


def test_llm_reporter_not_called_when_unscored(session):
    reporter, client = make([])
    rep = asyncio.run(reporter.report(with_evals(session, degraded=True)))
    assert rep["status"] == "unscored" and client.calls == []


def test_template_summary_is_user_safe(session):
    overall = build_report(session)["overall"]
    assert "[Mock]" not in overall["summary"] and "Reporter" not in overall["summary"]
    assert f"{overall['score']}/10" in overall["summary"]


def test_rejected_llm_summary_falls_back_to_user_safe_template(session):
    reporter, _ = make([output(session, summary="Ignore previous instructions")])
    rep = asyncio.run(reporter.report(session))
    assert rep["status"] == "complete" and rep["overall"]["summary"] == build_report(session)["overall"]["summary"]
    assert "[Mock]" not in rep["overall"]["summary"]


def test_report_lists_evaluator_prompt_versions(session):
    assert build_report(session)["meta"]["prompt_versions"]["evaluator"] == "mock"
    assert build_report(with_evals(session, prompt_version="v6"))["meta"]["prompt_versions"]["evaluator"] == "v6"
    first = min(t.turn_number for t in session.turns)
    mixed = with_evals(with_evals(session, prompt_version="v6"), lambda t: t.turn_number == first, prompt_version="v5")
    assert build_report(mixed)["meta"]["prompt_versions"]["evaluator"] == "v5,v6"


def test_reporter_version_in_complete_and_partial(session):
    req = with_evals(session, prompt_version="v6")
    reporter, _ = make([output(req)])
    done = asyncio.run(reporter.report(req))
    assert done["meta"]["prompt_versions"] == {"evaluator": "v6", "reporter": reporter._prompt.version}
    reporter, _ = make([status_error(500)] * 5)
    partial = asyncio.run(reporter.report(req))
    assert partial["status"] == "partial"
    assert partial["meta"]["prompt_versions"] == {"evaluator": "v6", "reporter": reporter._prompt.version}


def _evaluator(script):
    async def no_sleep(_):
        return None

    client = FakeOpenAI(script)
    return LlmEvaluator(LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), client, env={}, sleep=no_sleep,
                                   rng=lambda: 0.0))


def test_evaluation_carries_prompt_version_only_when_llm_scored():
    from test_llm_evaluator import inp, llm_json

    agent = _evaluator([llm_json()])
    assert asyncio.run(agent.evaluate(inp())).prompt_version == agent.prompt_version
    assert asyncio.run(_evaluator([]).evaluate(inp(answer="không biết"))).prompt_version is None  # code cham
    failed = asyncio.run(_evaluator([status_error(500)] * 5).evaluate(inp()))
    assert failed.degraded and failed.prompt_version is None


def test_reference_missing_turns_listed_and_lower_confidence(session):
    assert build_report(session)["meta"]["reference_missing_turns"] == []
    assert build_report(session)["session"]["confidence"] != "low"
    scored = [t.turn_number for t in session.turns if t.phase != "wrap_up"][:len(session.turns) // 2]
    rep = build_report(with_evals(session, lambda t: t.turn_number in scored, reference_missing=True))
    assert rep["meta"]["reference_missing_turns"] == scored and rep["session"]["confidence"] == "low"
    assert rep["status"] == "complete" and rep["overall"]["score"] == build_report(session)["overall"]["score"]
