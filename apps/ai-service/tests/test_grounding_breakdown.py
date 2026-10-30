"""Do nen Phase 05: tach `no_source`, suc khoe RAG, tai lieu Evaluator thay moi luot, chay service qua socket."""
import asyncio

import app.turn_engine as engine
from app.agents.evaluator import EvaluationInput, build_messages
from app.evaluator_source_checks import label
from app.logging_setup import bind_request
from app.models_interview import PlanTopic, SourceRef
from evals.sim_metrics import grounding, grounding_breakdown, rag_health
from evals.simulate import run_all
from evals.simulator import RuleSimulator
from evals.turn_source_recorder import attach_documents, documents, record_documents


def ref(value):
    return SourceRef(ref=value, title=value)


def turn(phase, kind, source, supports, docs=None):
    t = {"phase": phase, "turn_kind": kind, "question_source": source,
         "evaluation": {"evidence": [{"support": s} for s in supports], "confidence": "high"}}
    return t if docs is None else {**t, "documents": docs}


def input_with(reference="", snippets=("topic",), turn_chunks=("turn",)):
    topic = PlanTopic(id="t1", title="T", source="catalog", objective="o", key_points=["a", "b", "c"],
                      start_difficulty=2, opening_hint="h", backup_question="b", reference_snippets=list(snippets),
                      reference_sources=[ref("qa:1")][:len(snippets)])
    return EvaluationInput(level="junior", phase="technical", topic=topic, difficulty=2, turn_kind="main",
                           turn_number=4, question="q", answer="a", reference_answer=reference,
                           turn_snippets=list(turn_chunks), turn_sources=[ref("qa:2")][:len(turn_chunks)],
                           reference_source=ref("qa:3") if reference else None)


def test_breakdown_splits_no_source_by_where_it_happens():
    sessions = {"a": {"turns": [turn("intro", "main", "ai", ["no_source", "no_source"], []),
                                turn("technical", "follow_up", "ai", ["supported", "no_source"], [{"id": "S1"}]),
                                turn("technical", "main", "bank", ["supported"]),
                                {"phase": "wrap_up", "turn_kind": "main", "evaluation": None}]}}
    out = grounding_breakdown(sessions)
    assert out["phase"]["intro"] == {"points": 2, "supported": 0.0, "no_source": 1.0}
    assert out["phase"]["technical"]["points"] == 3 and out["phase"]["technical"]["supported"] == 0.667
    assert out["question_source"]["bank"]["supported"] == 1.0 and "wrap_up" not in out["phase"]
    assert out["no_source"] == {"no_documents": 2, "with_documents": 1, "unrecorded": 0}
    assert grounding(sessions)["points"] == 5 and grounding(sessions)["no_source"] == 0.6


def test_breakdown_without_recorded_documents_says_unrecorded_not_zero():
    sessions = {"a": {"turns": [turn("technical", "main", "ai", ["no_source"])]}}
    assert grounding_breakdown(sessions)["no_source"] == {"no_documents": 0, "with_documents": 0, "unrecorded": 1}


def test_refuted_points_are_counted_from_sources_because_evidence_never_has_them():
    evaluation = {"evidence": [{"support": "supported"}],
                  "sources": [{"id": "R", "support": "contradicted"}, {"id": "S2", "support": "contradicted"},
                              {"id": "S1", "support": "supported"}]}
    out = grounding({"a": {"turns": [{"evaluation": evaluation}, {"evaluation": {}}]}})
    assert out["points"] == 1 and out["supported"] == 1.0
    assert out["contradicted_sources"] == 2 and out["refuted_by_reference"] == 1


def test_rag_health_counts_request_status_and_skips_calls_without_rag():
    calls = [{"metadata": {"rag": {"status": "on"}}}, {"metadata": {"rag": {"status": "error"}}}, {"metadata": {}},
             {"path": "x"}]
    assert rag_health({"a": {"calls": calls}, "b": {"calls": calls[:1]}}) == {"on": 2, "error": 1}


def test_documents_keep_prompt_ids_and_origin():
    inp = input_with(reference="dap an")
    got = documents(inp)
    assert [(d["id"], d["origin"], d["ref"], d["text"]) for d in got] == [
        ("S1", "topic", "qa:1", "topic"), ("S2", "turn", "qa:2", "turn"), ("R", "reference", "qa:3", "dap an")]
    prompt = build_messages("sys", inp, True)[1]["content"]
    assert all(label(d["id"], d["text"]) in prompt for d in got)


def test_documents_of_turn_without_any_source_is_empty():
    assert documents(input_with(snippets=(), turn_chunks=())) == []


def test_recorder_passes_result_through_and_restores_evaluator():
    class Inner:
        async def evaluate(self, inp, collector=None):
            return "ket qua", collector

    real, inp = engine.get_evaluator, input_with()
    engine.get_evaluator = Inner
    try:
        bind_request("sim-a+b")
        with record_documents() as seen:
            assert asyncio.run(engine.get_evaluator().evaluate(inp, "c")) == ("ket qua", "c")
        assert engine.get_evaluator is Inner
    finally:
        bind_request(None)
        engine.get_evaluator = real
    same_turn_other_session = {"turns": [{"turn_number": 4}]}
    session = {"turns": [{"turn_number": 4}, {"turn_number": 5}]}
    attach_documents({"a+b": session, "c": same_turn_other_session}, seen)
    assert len(session["turns"][0]["documents"]) == 2 and "documents" not in session["turns"][1]
    assert "documents" not in same_turn_other_session["turns"][0]


def test_serve_measures_first_token_over_a_socket_and_records_documents(monkeypatch):
    monkeypatch.setenv("MOCK_STREAM_DELAY_MS", "5")  # token cach nhau 5 ms: stream bi dem thi gap ~ 0
    pid = "junior-java-strong"
    sessions = asyncio.run(run_all([pid], RuleSimulator(), serve=True))
    calls = [c for c in sessions[pid]["calls"] if c["path"] == "next-turn"]
    streamed = [c for c in calls if c["ttft_s"] is not None]
    assert streamed and all(c["total_s"] - c["ttft_s"] >= 0.01 for c in streamed)
    assert len(calls) - len(streamed) == 1  # luot tra loi cau wrap_up khong co token
    scored = [t for t in sessions[pid]["turns"] if t["evaluation"]]
    assert scored and all("documents" in t for t in scored)
