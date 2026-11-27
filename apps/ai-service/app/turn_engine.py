"""Orchestrator cho start / next-turn: start_session (Planner -> cau hoi dau) va next_turn (4 buoc turn_steps).

Luong moi luot (docs/ai-service/03): Evaluator cham -> cap nhat state -> policy chon action -> Interviewer dien dat.
next_turn() chay tuan tu 4 buoc cua turn_steps (duong goi ham truc tiep: test, evals in-process); endpoint HTTP chay
cung 4 buoc do qua graph LangGraph (app/turn_graph). TurnResult / finish_turn / flat_topics o turn_result, re-export.
"""
from typing import Optional

from .agents.evaluator_provider import Evaluator, get_evaluator  # noqa: F401  diem patch: turn_steps doc luc cham
from .agents.interviewer import QuestionSpec
from .agents.planner import get_planner
from .llm.usage import UsageCollector
from .mock_planner import load_track
from .models_common import LEVEL_CONFIG
from .models_interview import CandidateState, NextTurnRequest, StartRequest, TopicState, TurnInfo
from .plan_bank_coverage import prefer_covered, settle, start_coverage
from .plan_snippets import attach_reference_snippets, get_retriever
from .replan_reserve import with_reserve
from .tracing import observation
from .turn_result import TurnResult, _norm, finish_turn, flat_topics  # noqa: F401  re-export (API cu cua module)
from .turn_steps import SESSION_END, TurnContext, act_step, decide_step, evaluate_step, meta, perceive_step, \
    reask_step


async def start_session(req: StartRequest, planner=None, collector: Optional[UsageCollector] = None,
                        retriever=None) -> TurnResult:
    """Planner (LLM hoac mock, co plan du phong) -> doi topic khong co cau trong kho (dem song song voi Planner)
    -> gan reference_snippets (RAG, neu bat) -> cau hoi dau."""
    planner = planner or get_planner()
    catalog = load_track(req.track)
    counting = start_coverage(retriever or get_retriever(), catalog, req.level)
    plan = await planner.plan(req.track, req.level, req.duration_minutes, req.cv_profile, req.jd_profile, collector)
    keep = req.jd_profile.priority_topic_ids() if req.jd_profile else ()
    coverage = await settle(counting)
    plan = prefer_covered(plan, catalog, req.level, coverage, keep=keep)
    plan = with_reserve(plan, catalog, req.level, coverage, req.cv_profile, req.jd_profile)  # phase 05, chi khi co bat
    with observation("rag_plan", "retriever", nest=True) as obs:  # doc lai: ngat mach co the vua mo trong luc Planner
        plan = await attach_reference_snippets(plan, catalog, retriever or get_retriever(), collector)
        obs.update(output={t.id: [s.ref for s in t.reference_sources] for ph in plan.phases for t in ph.topics})
    topics = flat_topics(plan)
    lo, hi = LEVEL_CONFIG[req.level]["bounds"]
    first_phase, first = topics[0]
    state = CandidateState(
        phase=first_phase, topic_index=1, active_topic_id=first.id,
        current_difficulty=max(lo, min(hi, first.start_difficulty)), difficulty_bounds={"min": lo, "max": hi},
        turn_count=1, phase_started_s=0, topic_started_s=0, topics=[TopicState(id=t.id, status="active" if i == 0 else "pending")
                              for i, (_, t) in enumerate(topics)])
    spec = QuestionSpec("ask_main", first_phase, first, state.current_difficulty, first_turn=True)
    state.topics[0].turns.append(1)
    turn = TurnInfo(turn_number=1, phase=first_phase, topic_id=first.id, turn_kind="main", action="ask_main",
                    agent_decision="switch_topic", difficulty=state.current_difficulty)
    return TurnResult(spec, turn, state, plan, None, False, meta(first_phase, 1, len(topics), "ask_main", 1))


def turn_context(req: NextTurnRequest, evaluator: Optional[Evaluator] = None,
                 collector: Optional[UsageCollector] = None, retriever=None, interviewer=None) -> TurnContext:
    """Ngu canh mot luot. Evaluator None: turn_steps lay get_evaluator() cua module nay khi can cham (test / evals
    patch o day). interviewer: ham tra Interviewer, chi node `ask` cua graph goi."""
    return TurnContext(req, evaluator, collector, retriever, interviewer)


async def next_turn(req: NextTurnRequest, evaluator: Optional[Evaluator] = None,
                    collector: Optional[UsageCollector] = None, retriever=None) -> TurnResult:
    """Perceive -> (reask | Evaluate -> Decide -> Act), tuan tu; graph LangGraph di cung cac buoc nay."""
    ctx = turn_context(req, evaluator, collector, retriever)
    route = perceive_step(ctx)
    if route == "reask":
        reask_step(ctx)
    elif route == "evaluate":
        await evaluate_step(ctx)
        if decide_step(ctx) != SESSION_END:
            act_step(ctx)
    return ctx.result
