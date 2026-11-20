"""Lap lai ke hoach (phase 05, review M2): cac reader sau khi doi topic doc dung topic thuc te (alt1): do phu yeu cau JD,
tai lieu / nguon cua bao cao, low_performance_stop doc diem that cua topic moi. Khong monkeypatch quyet dinh."""
import copy

from app.models_interview import CandidateState, FinalizeRequest
from app.models_jd import JdProfile, JdRequirement
from app.replan import apply_swap, effective_plan
from app.report_resources import plan_sources
from app.report_scoring import build_report
from app.early_stop import low_performance_stop
from app.models_evaluation import SourceRef
from app.turn_engine import flat_topics, next_turn
from tests.test_policy_hybrid import WEAK
from tests.test_policy_hybrid_turn_engine import ProposalEvaluator
from tests.test_replan import sw, started
from tests.test_replan_sim import play
from tests.test_replan_turn_engine import req_at_t2, run


def finalize_request(session, jd=None, mutate=None):
    """FinalizeRequest tu mot phien sim da doi t4 -> alt1 (plan goc + state.swaps; effective_plan do main ap)."""
    plan = copy.deepcopy(session["plan"])
    if mutate:
        mutate(plan)
    turns = [{k: t[k] for k in ("turn_number", "phase", "topic_id", "turn_kind", "difficulty", "question", "answer",
                                "evaluation")} for t in copy.deepcopy(session["turns"])]
    state = CandidateState(phase="done", swaps=session["swaps"])
    return FinalizeRequest.model_validate({
        "session_id": "x", "track": "java_backend", "level": "junior", "plan": plan, "state": state.model_dump(),
        "end_reason": "plan_complete", "duration_s": 600, "turns": turns,
        "jd_profile": jd.model_dump() if jd else None}), turns


def test_jd_requirement_mapped_to_the_swapped_in_topic_counts_as_assessed(client, monkeypatch):
    s = play(monkeypatch)["junior-java-average"]
    alt = s["plan"]["replan"]["reserve"][0]
    jd = JdProfile(requirements=[JdRequirement(id="r1", text="Cache", kind="must", topic_ids=[alt["catalog_ref"]])])
    req, turns = finalize_request(s, jd)
    assert any(t["topic_id"] == "alt1" for t in turns)
    body = {**req.model_dump(), "jd_profile": jd.model_dump()}
    block = client.post("/api/finalize", json=body).json()["requirements"]
    assert block["assessed"] == 1 and block["items"][0]["status"] == "assessed" and block["items"][0]["evidence_turns"]
    body["state"]["swaps"] = []  # khong co swaps: alt* khong nam trong plan.phases -> yeu cau nay not_assessed
    assert client.post("/api/finalize", json=body).json()["requirements"]["items"][0]["status"] == "not_assessed"


def test_report_resources_and_sources_use_the_swapped_in_topic(monkeypatch):
    s = play(monkeypatch)["junior-java-average"]
    ref = SourceRef(ref="doc-alt1", title="Tài liệu Cache", license="CC-BY")

    def attach(plan):
        plan["replan"]["reserve"][0]["reference_sources"] = [ref.model_dump()]
        plan["replan"]["reserve"][0]["reference_snippets"] = ["Cache giúp giảm tải DB."]
    req, turns = finalize_request(s, mutate=attach)
    eff = effective_plan(req.plan, req.state)
    assert plan_sources(eff)["alt1"] == [ref] and "t4" not in plan_sources(eff) and "alt1" not in plan_sources(req.plan)
    for t in req.turns:  # alt1 yeu de vao study_plan
        if t.topic_id == "alt1" and t.evaluation:
            t.evaluation.turn_score_10 = 1.0
            t.evaluation.scores_10 = t.evaluation.scores_10.model_copy(update={
                k: 1.0 for k in ("technical_accuracy", "completeness", "extensibility", "relevance")})
    report = build_report(req.model_copy(update={"plan": eff}))
    item = next(i for i in report["study_plan"] if i["topic"] == eff.replan.reserve[0].title)
    assert [r["title"] for r in item["resources"]] == ["Tài liệu Cache"]
    assert "alt1" in [t["topic_id"] for t in report["topics"]]


def test_low_performance_stop_reads_the_swapped_in_topics_real_score(monkeypatch):
    r = started(monkeypatch, level="middle")  # t1 intro, t2-t4 technical, t5 scenario
    apply_swap(r.state, sw("t4", "alt1"), 3, 3)
    topics = flat_topics(effective_plan(r.plan, r.state))
    assert [t.id for _, t in topics][3] == "alt1"
    r.state.evaluated_turns = 6
    for i, band in ((1, 0.5), (2, 1.0), (3, 1.4)):
        r.state.topics[i].score_band = band
    assert low_performance_stop(r.state, topics, 3, "middle", "next_topic")
    r.state.topics[3].score_band = 3.0  # alt1 manh: chuoi yeu bi cat
    assert not low_performance_stop(r.state, topics, 3, "middle", "next_topic")


def test_weak_swapped_in_topic_ends_the_session_early_through_next_turn(monkeypatch):
    monkeypatch.delenv("POLICY_MODE", raising=False)  # rules: de luat quyet dinh, khong dung de xuat LLM
    monkeypatch.delenv("REPLAN_ENABLED", raising=False)
    r = started(monkeypatch, level="middle")
    monkeypatch.delenv("POLICY_MODE", raising=False)
    monkeypatch.delenv("REPLAN_ENABLED", raising=False)
    apply_swap(r.state, sw("t4", "alt1"), 3, 2)
    st = r.state
    for i, band in ((1, 0.5), (2, 1.0)):
        st.topics[i].status, st.topics[i].score_band = "done", band
    st.topics[0].status, st.topics[3].status = "done", "active"
    st.topics[3].n_scored, st.topics[3].score_sum, st.topics[3].score_band = 1, 1.0, 1.0
    st.phase, st.active_topic_id, st.evaluated_turns, st.topic_index = "technical", "alt1", 6, 3
    st.counters.follow_ups, st.counters.hints = 9, 1  # het ngan sach: luat chon next_topic
    req = req_at_t2(monkeypatch, r).model_copy(update={"level": "middle", "elapsed_seconds": 120})
    res = run(next_turn(req, evaluator=ProposalEvaluator(WEAK)))
    assert req.state.active_topic_id == "alt1" and res.state.end_reason == "low_performance"
    assert res.turn.action == "wrap_up"
