"""Lap lai ke hoach (phase 05) qua next_turn: doi tai cho, bac, forced / turn cap / low_performance o tren LLM, co tat =
y cu, plan cu. Evaluator gia, khong goi LLM that."""
import asyncio
import copy

import pytest

from app import metrics
from app.models_interview import NextTurnRequest
from app.replan import effective_plan
from app.time_budget import phase_deadline_s
from app.turn_engine import finish_turn, flat_topics, next_turn
from tests.test_policy_hybrid import OK
from tests.test_policy_hybrid_turn_engine import ProposalEvaluator
from tests.test_replan import sw, started, v10, on

DONE_OK = OK.model_copy(update={"missing_points": []})  # luat chon next_topic


def run(coro):
    return asyncio.run(coro)


def req_at_t2(monkeypatch, r=None, elapsed=60):
    """Dang o topic technical dau (t2, pos 1) cua plan 30 phut co reserve."""
    r = r or started(monkeypatch)
    finish_turn(r, "Câu hỏi?", "ai")
    return NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=r.plan, state=r.state, turn_number=3,
                           question="Câu hỏi?", turn_kind="main", answer="Em dùng @Transactional cho service.",
                           elapsed_seconds=elapsed)


def step(req, evaluator):
    res = run(next_turn(req, evaluator=evaluator))
    finish_turn(res, "Câu tiếp?", "ai")
    return res, req.model_copy(update={"state": res.state, "question": res.question, "turn_number": res.turn.turn_number,
                                       "turn_kind": res.turn.turn_kind})


def test_applied_swap_replaces_the_topic_in_place_and_later_turns_ask_it(monkeypatch):
    req = req_at_t2(monkeypatch)
    before = metrics.REPLAN_SWAPS.labels("applied")._value.get()
    ev = ProposalEvaluator(DONE_OK, v10(sw("t4", "alt1")))
    res, req = step(req, ev)
    assert res.turn.swap_result == "applied" and res.turn.topic_id == "t3"  # next_topic -> t3 (pos 2)
    assert (res.state.swaps[0].drop, res.state.swaps[0].add) == ("t4", "alt1")
    assert res.state.swaps[0].turn == 3 and res.state.topics[3].id == "alt1" and res.state.topics[3].status == "pending"
    assert metrics.REPLAN_SWAPS.labels("applied")._value.get() == before + 1
    assert req.plan is not None and [t.id for _, t in flat_topics(req.plan)][3] == "t4"  # plan gui client khong doi
    assert res.meta["topic_total"] == 6  # doi 1:1: khong doi so topic
    res2, req = step(req, ev)  # t3 xong: swap lan 2 bi bac (budget), topic ke la alt1 (khong con t4)
    assert res2.turn.topic_id == "alt1" and res2.turn.swap_result == "budget" and len(res2.state.swaps) == 1
    assert res2.spec.topic.id == "alt1" and res2.spec.topic.title == req.plan.replan.reserve[0].title
    res3, req = step(req, ev)  # luot cham alt1: Evaluator thay topic du phong
    assert ev.last_input.topic.id == "alt1" and res3.turn.topic_id == "t5"
    assert [t.id for t in res3.state.topics] == [t.id for _, t in flat_topics(effective_plan(req.plan, res3.state))]


@pytest.mark.parametrize("keep,drop,why", [(["t4"], "t4", "jd_priority"), ([], "t2", "bad_drop"),
                                           ([], "t6", "bad_drop"), ([], "t1", "bad_drop"), ([], "zzz", "bad_drop")])
def test_rejected_swap_changes_nothing_but_the_result_label(monkeypatch, keep, drop, why):
    r = started(monkeypatch)
    r.plan.replan.keep_ids = keep
    req = req_at_t2(monkeypatch, r)
    base = run(next_turn(req.model_copy(deep=True), evaluator=ProposalEvaluator(DONE_OK, v10(None))))
    res = run(next_turn(req.model_copy(deep=True), evaluator=ProposalEvaluator(DONE_OK, v10(sw(drop, "alt1")))))
    assert res.turn.swap_result == why and res.state.swaps == []
    assert res.state.model_dump_json() == base.state.model_dump_json() and base.turn.swap_result is None
    assert res.turn.model_dump(exclude={"swap_result"}) == base.turn.model_dump(exclude={"swap_result"})


def test_swap_never_overrides_forced_time_turn_cap_or_low_performance(monkeypatch):
    prop = v10(sw("t4", "alt1"), next_action="next_topic")
    ev = lambda: ProposalEvaluator(DONE_OK, prop)  # noqa: E731
    cases = {"time": lambda q: q.model_copy(update={"elapsed_seconds": 30 * 60}),
             "turn_cap": lambda q: (setattr(q.state, "turn_count", 999), q)[1]}
    for name, tweak in cases.items():
        res = run(next_turn(tweak(req_at_t2(monkeypatch)), evaluator=ev()))
        assert res.turn.action == "wrap_up" and res.turn.decided_by == "forced", name
        assert res.turn.swap_result == "not_applicable" and res.state.swaps == [], name
    monkeypatch.setattr("app.turn_decision.low_performance_stop", lambda *a, **k: True)
    res = run(next_turn(req_at_t2(monkeypatch), evaluator=ev()))
    assert res.turn.action == "wrap_up" and res.state.end_reason == "low_performance"
    assert res.turn.swap_result == "not_applicable" and res.state.swaps == []


def test_forced_next_topic_two_dont_know_and_hurry_are_not_swapped(monkeypatch):
    req = req_at_t2(monkeypatch)
    req.state.counters.consecutive_dont_know = 1
    dk = OK.model_copy(update={"answer_type": "dont_know"})
    res = run(next_turn(req, evaluator=ProposalEvaluator(dk, v10(sw("t4", "alt1")))))
    assert res.turn.decided_by == "forced" and res.turn.swap_result == "not_applicable" and res.state.swaps == []
    hurry = req_at_t2(monkeypatch)
    left = 10  # con 10 s toi han phase technical: time_hint = hurry, chua forced
    hurry.elapsed_seconds = phase_deadline_s(hurry.plan, "technical") - left
    hurry.state.topic_started_s = hurry.state.phase_started_s = hurry.elapsed_seconds - 10
    res = run(next_turn(hurry, evaluator=ProposalEvaluator(DONE_OK, v10(sw("t4", "alt1")))))
    assert res.turn.decided_by == "llm" and res.turn.swap_result == "budget" and res.state.swaps == []


def test_flag_off_requests_and_outputs_are_identical_to_before(monkeypatch):
    """Co tat (mac dinh / false) hoac rules: Evaluator khong nhan replan_context, de xuat swap bi bo qua, turn / state y
    het khi LLM khong de xuat swap; chi them khoa mac dinh swap_result: null / swaps: []."""
    base = started(monkeypatch)  # co plan.replan (bat hybrid + replan chi de dung plan); roi dat env that cua tung ca
    rules, hybrid_off = set(), set()
    for env, bucket in (({}, rules), ({"REPLAN_ENABLED": "false"}, rules), ({"REPLAN_ENABLED": "true"}, rules),
                        ({"POLICY_MODE": "hybrid", "REPLAN_ENABLED": "false"}, hybrid_off),
                        ({"POLICY_MODE": "hybrid"}, hybrid_off)):
        for k in ("REPLAN_ENABLED", "POLICY_MODE"):
            monkeypatch.delenv(k, raising=False)
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        for proposal in (v10(sw("t4", "alt1")), v10(None)):  # rules khong dung de xuat: cung ket qua ca khi None
            ev = ProposalEvaluator(DONE_OK, proposal)
            res = run(next_turn(req_at_t2(monkeypatch, copy.deepcopy(base)), evaluator=ev))
            assert ev.last_input.replan_context is None and res.state.swaps == [] and res.turn.swap_result is None
            bucket.add((res.turn.model_dump_json(), res.state.model_dump_json()))
    assert len(rules) == 1 and len(hybrid_off) == 1  # swap duoc de xuat hay khong: khong doi gi


def test_hybrid_on_gives_the_evaluator_a_context_only_at_a_boundary_with_reserve(monkeypatch):
    ev = ProposalEvaluator(DONE_OK, v10(None))
    run(next_turn(req_at_t2(monkeypatch), evaluator=ev))
    rc = ev.last_input.replan_context
    assert [i for i, _ in rc.reserve] == ["alt1", "alt2"] and rc.swaps_left == 1 and rc.band is None
    assert {"t4", "t5"} <= {i for i, _ in rc.pending} and "t6" not in {i for i, _ in rc.pending}


def test_old_plan_and_state_without_replan_run_as_before(monkeypatch):
    on(monkeypatch)
    r = started(monkeypatch)
    plain = r.plan.model_copy(update={"replan": None})
    req = req_at_t2(monkeypatch, r).model_copy(update={"plan": plain})
    ev = ProposalEvaluator(DONE_OK, v10(sw("t4", "alt1")))
    res = run(next_turn(req, evaluator=ev))
    assert ev.last_input.replan_context is None and res.turn.swap_result == "budget" and res.state.swaps == []


