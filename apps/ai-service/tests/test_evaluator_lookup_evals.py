"""Phase 03: cong cu do (evals) cho Evaluator tra cuu: recorder, --lookup, chi so mo phong, TTFT tach luot tra cuu."""
import asyncio

from app.agents.evaluator import EvaluationInput
from app.evaluator_lookup import TurnLookup, load_lookup_settings
from app.models_interview import Evaluation, SourceRef
from evals.lookup_support import attach_lookup, lookup_fields, lookup_summary
from evals.sim_lookup_metrics import evaluator_lookup
from evals.ttft_breakdown import FALLBACK_KINDS, breakdown, turn_rows
from evals.turn_source_recorder import _RecordingEvaluator, documents
from tests.test_evaluator_lookup import Recorder, chunk
from tests.test_rag_turn_retrieval import retriever, topic

ON = load_lookup_settings({"EVALUATOR_TOOLS": "true"})


def base_input():
    return EvaluationInput(level="junior", phase="technical", topic=topic(), difficulty=1, turn_kind="main",
                           turn_number=3, question="q", answer="a", turn_snippets=["turn chunk"],
                           turn_sources=[SourceRef(ref="r1", title="t")])


class FakeInner:
    supports_lookup = True

    def __init__(self, commit: bool):
        self.commit = commit

    async def evaluate(self, inp, collector=None):
        inp.lookup.texts.append("tool chunk")
        inp.lookup.sources.append(SourceRef(ref="r2", title="t"))
        inp.lookup.committed = self.commit
        return Evaluation(turn_number=3, answer_type="answered",
                          scores={k: 2 for k in ("technical_accuracy", "completeness", "extensibility", "relevance")},
                          scores_10={k: 5.0 for k in ("technical_accuracy", "completeness", "extensibility",
                                                      "relevance")}, turn_score_10=5.0)


def record(commit: bool):
    inp = base_input()
    inp.lookup = TurnLookup(Recorder(), [*inp.topic.reference_snippets, "turn chunk"],
                            len(inp.topic.reference_snippets) + 1, ON)
    seen = {}
    wrapped = _RecordingEvaluator(FakeInner(commit), seen)
    assert wrapped.supports_lookup  # lop boc khong chan tra cuu trong mo phong
    asyncio.run(wrapped.evaluate(inp))
    return next(iter(seen.values()))


def test_recorder_sees_tool_chunks_only_when_loop_committed():
    committed, failed = record(True), record(False)
    assert [d["origin"] for d in committed][-2:] == ["turn", "tool"] and committed[-1]["text"] == "tool chunk"
    assert "tool" not in {d["origin"] for d in failed}  # vong lap loi: model khong thay chunk nao ma duoc cham


def test_documents_marks_tool_origin_from_tool_base_ids():
    inp = base_input()
    inp.lookup = TurnLookup(Recorder(), [], 1, ON)
    inp.lookup.texts, inp.lookup.sources = ["T"], [SourceRef(ref="x", title="t")]
    docs = documents(inp.lookup.extend(inp))
    assert docs[-1]["origin"] == "tool" and docs[-1]["id"] == f"S{len(docs)}"


def sample(**kw):
    return {"id": "x", "track": "java_backend", **kw}


def test_attach_lookup_gives_fresh_state_per_run_and_skips_reference_and_missing_retriever():
    r = retriever()
    a, b = base_input(), base_input()
    la, lb = attach_lookup(r, sample(), a), attach_lookup(r, sample(), b)
    assert la is not None and la is not lb and a.lookup is la
    withref = base_input()
    withref.reference_answer = "R"
    assert attach_lookup(r, sample(), withref) is None and withref.lookup is None
    assert attach_lookup(None, sample(), base_input()) is None
    intro = base_input()
    intro.phase = "intro"
    assert attach_lookup(r, sample(), intro) is None


def test_lookup_summary_rates():
    lk = TurnLookup(Recorder(), [], 0, ON)
    lk.queries, lk.texts, lk.committed = ["q"], ["t"], True
    hit = lookup_fields(lk)
    empty = lookup_fields(TurnLookup(Recorder(), [], 0, ON)) | {"tool_queries": 1, "lookup_committed": True}
    failed = {**hit, "lookup_committed": False}
    assert lookup_summary([{}, {"x": 1}]) == {"eligible_runs": 0}
    out = lookup_summary([hit, empty, failed, {"lookup": False}])
    assert out == {"eligible_runs": 3, "lookup_rate": 1.0, "empty_rate": 0.333, "loop_failed": 1}


def turn(i, ta, miscon=(), docs=None, qa=None, phase="technical"):
    t = {"turn_number": i, "phase": phase, "qa_id": qa,
         "evaluation": {"scores": {"technical_accuracy": ta}, "misconceptions": list(miscon)}}
    if docs is not None:
        t["documents"] = docs
    return t


def call(tool_calls=0, fallbacks=()):
    usage = {"evaluator": {"tool_calls": tool_calls} if tool_calls else {}}
    return {"path": "next-turn", "metadata": {"usage": usage, "fallbacks": list(fallbacks)}}


def test_sim_lookup_metrics_count_only_eligible_turns():
    tool_doc, ref_doc = [{"origin": "tool"}], [{"origin": "reference"}]
    calls = [{"path": "start"}, call(1), call(1, ["evaluator_lookup_fallback"]), call(), call(), call()]
    sessions = {"p": {"calls": calls,
                      "turns": [turn(1, 3, docs=tool_doc), turn(2, 1, ["m"], docs=[]), turn(3, 2, docs=ref_doc),
                                turn(4, 4, phase="intro"), turn(5, 0, ["m"], docs=[], qa=None)]}}
    out = evaluator_lookup(sessions)
    assert out["eligible_turns"] == 3 and out["lookup_turns"] == 1  # tru R, intro, vong lap loi (turn 2)
    assert out["lookup_rate"] == 0.333 and out["empty_rate"] == 0.0
    assert out["misconception_rate"] == 0.667 and out["ta_le1_rate"] == 0.667 and out["lookup_fallback"] == 1


def test_sim_lookup_metrics_failed_loops_are_not_lookups_or_empty():
    calls = [{"path": "start"}, call(1, ["evaluator_lookup_fallback"]), call(1)]
    sessions = {"p": {"calls": calls, "turns": [turn(1, 2, docs=[]), turn(2, 2, docs=[{"origin": "tool"}])]}}
    out = evaluator_lookup(sessions)
    assert out["lookup_turns"] == 1 and out["lookup_rate"] == 0.5 and out["empty_rate"] == 0.0
    assert out["lookup_fallback"] == 1


def test_sim_lookup_metrics_empty_sessions():
    out = evaluator_lookup({"p": {"calls": [], "turns": []}})
    assert out["eligible_turns"] == 0 and out["lookup_rate"] is None


def ttft_call(ttft, tool_calls=0, fallbacks=()):
    usage = {"input_tokens": 4000, "output_tokens": 150, **({"tool_calls": tool_calls} if tool_calls else {})}
    return {"path": "next-turn", "ttft_s": ttft, "total_s": ttft + 1,
            "metadata": {"latency_ms": {"evaluator": 2000, "interviewer": 1000, "total": 0},
                         "usage": {"evaluator": usage}, "fallbacks": list(fallbacks)}}


def test_ttft_breakdown_separates_lookup_and_counts_lookup_fallback():
    assert "evaluator_lookup_fallback" in FALLBACK_KINDS
    calls = [ttft_call(3.0), ttft_call(3.2), ttft_call(3.1), ttft_call(5.0, tool_calls=1),
             ttft_call(9.0, tool_calls=1, fallbacks=["evaluator_lookup_fallback"])]
    out = breakdown(turn_rows({"p": {"calls": calls}}))
    assert out["normal"]["turns"] == 3 and out["lookup"]["turns"] == 1 and out["lookup"]["ttft"]["p50"] == 5.0
    assert out["fallback"]["evaluator_lookup_fallback"]["turns"] == 1
    assert "lookup" not in breakdown(turn_rows({"p": {"calls": calls[:3]}}))
