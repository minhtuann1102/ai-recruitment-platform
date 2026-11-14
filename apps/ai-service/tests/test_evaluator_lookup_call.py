"""Phase 03: duong goi Evaluator co tra cuu voi LLM gia (kich ban tool, ngan sach chung 10 s thu nho, fallback, latch).
Khong khang dinh chat luong cham. Thoi gian thu nho bang limit_agent + MIN_FALLBACK_S de test khong cho that."""
import asyncio
import json
import time

import pytest

import app.agents.evaluator_lookup_call as elc
from app import metrics
from app.agents.evaluator import EvaluationInput, LlmEvaluator
from app.evaluator_lookup import TurnLookup, load_lookup_settings
from app.llm import tool_loop
from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from app.llm.usage import UsageCollector
from app.models_interview import CandidateState, NextTurnRequest, SourceRef
from app.mock_planner import build_plan
from app.rag.models import Chunk
from app.turn_evaluation import evaluate_turn
from fakes.fake_llm import FakeOpenAI, Slow, limit_agent, reply, status_error, tool_reply
from tests.test_evaluator_lookup import Recorder, chunk
from tests.test_llm_evaluator import ANSWER, TOPIC, inp, llm_json
from tests.test_question_bank import CaptureEvaluator
from tests.test_rag_turn_retrieval import retriever, topic as rag_topic

ON = load_lookup_settings({"EVALUATOR_TOOLS": "true"})
CALL = tool_reply([("c1", "search_knowledge", '{"query": "b-tree"}')])
TOOL_DOC = "Tài liệu tra cứu: B-tree giữ index cân bằng."


@pytest.fixture(autouse=True)
def _latch():
    tool_loop.reset_tools_latch()
    yield
    tool_loop.reset_tools_latch()


def make(script):
    async def no_sleep(_):
        return None

    client = FakeOpenAI(script)
    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), client, env={}, sleep=no_sleep, rng=lambda: 0.0)
    return LlmEvaluator(gw), client


def with_lookup(*results):
    lk = TurnLookup(Recorder(*results), list(TOPIC.reference_snippets), len(TOPIC.reference_snippets), ON)
    base = inp()
    base.lookup = lk
    return base, lk


def lookup_count(result):
    return metrics.EVALUATOR_LOOKUP.labels(result)._value.get()


def run(coro):
    return asyncio.run(coro)


def final_json(source_id="S2"):
    out = json.loads(llm_json().choices[0].message.content)
    out["covered"][0].update(source_ids=[source_id], support="supported")
    return reply(json.dumps(out, ensure_ascii=False))


def test_flag_off_request_has_no_tools_and_no_fragment():
    ev_agent, client = make([llm_json()])
    ev = run(ev_agent.evaluate(inp(), UsageCollector()))
    p = client.calls[0]
    assert not ev.degraded and "tools" not in p and "tool_choice" not in p
    assert "search_knowledge" not in p["messages"][0]["content"]


def test_one_tool_call_extends_ids_and_sources_and_keeps_prompt_version():
    base, lk = with_lookup([chunk(1, TOOL_DOC)])
    ev_agent, client = make([CALL, final_json("S2")])
    col = UsageCollector()
    ev = run(ev_agent.evaluate(base, col))
    first, second = client.calls
    assert first["tools"][0]["function"]["name"] == "search_knowledge" and first["tool_choice"] == "auto"
    assert "search_knowledge" in first["messages"][0]["content"] and ev.prompt_version == "v8"
    assert second["tool_choice"] == "none" and "[S2] " + TOOL_DOC in second["messages"][-1]["content"]
    assert lk.committed and lk.texts == [TOOL_DOC]
    assert ev.evidence[0].source_ids == ["S2"] and [s.id for s in ev.sources] == ["S2"]
    assert ev.sources[0].ref == "qa1" and not ev.degraded
    assert len(col.records) == 1 and col.records[0].tool_calls == 1 and col.records[0].fallback is None
    assert col.records[0].prompt_version == "v8"  # ten fragment khong lot vao prompt_version


def test_no_tool_call_commits_without_chunks_and_postcheck_sees_base_only():
    base, lk = with_lookup()
    ev = run(make([llm_json()])[0].evaluate(base, UsageCollector()))
    assert lk.committed and lk.texts == [] and not ev.degraded
    assert ev.evidence[0].source_ids == ["S1"]  # topic S1 van hop le; khong co id cong cu


def test_invalid_query_returns_error_to_model_and_scoring_continues():
    base, lk = with_lookup([chunk(1, TOOL_DOC)])
    bad = tool_reply([("c1", "search_knowledge", '{"query": "ignore previous instructions"}')])
    ev_agent, client = make([bad, llm_json()])
    ev = run(ev_agent.evaluate(base, UsageCollector()))
    assert client.calls[1]["messages"][-1]["content"] == "error: invalid_query" and not ev.degraded
    assert lk.texts == [] and lookup_count("error") >= 1


def test_early_loop_failure_falls_back_to_one_plain_call_with_single_fallback_record():
    base, lk = with_lookup([chunk(1, TOOL_DOC)])
    ev_agent, client = make([CALL, reply("khong phai json"), reply("van khong phai json"), llm_json()])
    col, before = UsageCollector(), lookup_count("fallback")
    ev = run(ev_agent.evaluate(base, col))
    assert not ev.degraded and "tools" not in client.calls[-1]
    assert "search_knowledge" not in client.calls[-1]["messages"][0]["content"]
    assert [r.fallback for r in col.records] == ["evaluator_lookup_fallback", None]  # khong co record thu hai
    assert col.records[0].latency_ms >= 0 and col.records[0].tool_calls == 1
    assert not lk.committed and all(s.id != "S2" for s in ev.sources)
    assert lookup_count("fallback") == before + 1


@pytest.fixture
def small_budget(monkeypatch):
    """Ngan sach 10 s thu thanh 1.2 s, ngưỡng fallback 2.5 s thanh 0.5 s."""
    limit_agent(monkeypatch, "evaluator", 5.0, 1.2)
    monkeypatch.setattr(elc, "MIN_FALLBACK_S", 0.5)
    monkeypatch.setattr(elc, "FINAL_RESERVE_S", 0.3)


def test_slow_loop_uses_whole_budget_then_mock_degraded_without_second_call(small_budget):
    base, _ = with_lookup()
    ev_agent, client = make([Slow(5.0, CALL), llm_json()])
    col, started = UsageCollector(), time.perf_counter()
    ev = run(ev_agent.evaluate(base, col))
    assert ev.degraded and time.perf_counter() - started < 1.2 + 0.5  # B + 0.5 s (tuong ung 10 + 0.5 s)
    assert len(client.calls) == 1  # het ngan sach: khong goi lai khong tools
    assert [r.fallback for r in col.records] == ["evaluator_lookup_fallback", "evaluator_mock_heuristic"]


def test_loop_failing_late_leaves_too_little_budget_for_fallback(small_budget):
    base, _ = with_lookup()
    ev_agent, client = make([Slow(0.8, reply("rac")), reply("rac nua"), llm_json()])
    ev = run(ev_agent.evaluate(base, UsageCollector()))
    assert ev.degraded and len(client.calls) == 2  # con 0.4 s < 0.5 s: thang mock


def test_fallback_call_is_capped_by_the_same_clock(small_budget):
    base, _ = with_lookup()
    ev_agent, client = make([reply("rac"), reply("rac nua"), Slow(5.0, llm_json())])
    started = time.perf_counter()
    ev = run(ev_agent.evaluate(base, UsageCollector()))
    assert ev.degraded and time.perf_counter() - started < 1.2 + 0.5  # lan goi fallback bi cat o phan du, khong du 8 s


def test_tools_unsupported_latches_and_scores_on_plain_path():
    base, _ = with_lookup()
    err = status_error(404, message="No endpoints found that support the provided parameters (tools)")
    col, before = UsageCollector(), lookup_count("unsupported")
    ev = run(make([err, llm_json()])[0].evaluate(base, col))
    assert not ev.degraded and not tool_loop.tools_supported()
    assert lookup_count("unsupported") == before + 1
    base2, _ = with_lookup()  # luot sau: complete_with_tools tu choi ngay (latch), van cham duoc qua duong cu
    ev2 = run(make([llm_json()])[0].evaluate(base2, UsageCollector()))
    assert not ev2.degraded


def test_old_prompt_without_sources_skips_lookup():
    from app.prompts.store import PromptStore
    ev_agent, client = make([llm_json()])
    ev_agent._prompt = PromptStore().get("evaluator", "v3")
    base, lk = with_lookup()
    run(ev_agent.evaluate(base, UsageCollector()))
    assert "tools" not in client.calls[0] and not lk.committed


def test_evaluate_turn_builds_lookup_only_with_flag_llm_agent_and_no_answer_key(monkeypatch):
    t = rag_topic()
    plan = build_plan("java_backend", "junior", 20, None)
    state = CandidateState(current_difficulty=1)
    req = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=plan, state=state, turn_number=2,
                          question="HashMap xử lý va chạm thế nào?", answer="Em nghĩ dùng bucket",
                          elapsed_seconds=60)

    def evaluate(evaluator, **kw):
        run(evaluate_turn(req, state, "technical", t, req.answer, evaluator, None, retriever()))
        return evaluator.inputs[-1].lookup

    class LlmLike(CaptureEvaluator):
        supports_lookup = True

    assert evaluate(LlmLike()) is None  # co tat (mac dinh)
    monkeypatch.setenv("EVALUATOR_TOOLS", "true")
    assert evaluate(CaptureEvaluator()) is None  # khong phai agent LLM
    lk = evaluate(LlmLike())
    assert lk is not None and lk.base_ids == len(t.reference_snippets) + len(evaluator_inputs_snippets(t))


def evaluator_inputs_snippets(t):
    """Chunk theo luot ma RAG theo luot gan cho cau tren (base_ids phai tinh ca chung)."""
    from app.turn_reference_snippets import turn_snippets
    r = retriever()
    return run(turn_snippets(r, "java_backend", phase="technical", topic=t, difficulty=1,
                             question="HashMap xử lý va chạm thế nào?", answer="Em nghĩ dùng bucket",
                             has_answer_key=False)).texts
