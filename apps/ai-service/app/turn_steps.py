"""Bon buoc cua mot luot next-turn (Perceive -> Evaluate -> Decide -> Act, docs/ai-service/03 + 12).

Than cu cua turn_engine.next_turn() tach nguyen van thanh 4 ham tren mot TurnContext: next_turn() goi tuan tu, graph
LangGraph (app/turn_graph) goi tung buoc lam node. Logic, thu tu kiem, guard khong doi; golden trace
(tests/test_golden_turns_match_fixture.py) giu hai duong cho cung ket qua.
Buoc tra ve "route" cho canh tiep: perceive -> session_end | reask | evaluate; decide -> session_end | hanh dong cua
Decision. SESSION_END tach khoi ten hanh dong (Decision.action khong bao gio la "session_end").
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .agents.interviewer import QuestionSpec, safe_focus
from .api_error import ApiError
from .llm.usage import UsageCollector
from .models_interview import CandidateState, Evaluation, InterviewPlan, NextTurnRequest, PlanTopic, TurnInfo
from .rag.difficulty import difficulty_bucket
from .rag.question_bank import pick
from .replan import check_alignment, effective_plan
from .state_update import apply_action, record_evaluation
from .time_budget import forced_transition
from .turn_decision import DecisionTrace, choose_decision, time_hint
from .turn_evaluation import evaluate_turn, hint_source
from .turn_reference_snippets import TurnChunks
from .turn_result import TurnResult, flat_topics
from .voice_turn import MAX_REASKS, heard_answer, low_confidence, no_speech, \
    reask_spec, reject_no_speech, reject_unclear, unclear_evaluation

_KIND = {"ask_main": "main", "follow_up": "follow_up", "hint": "hint", "clarify": "clarify",
         "wrap_up": "main", "end": "main"}  # next_topic / next_phase deu thanh ask_main sau apply_action
_AGENT = {"follow_up": "deepen", "hint": "keep_difficulty", "clarify": "keep_difficulty"}
NO_REFERENCE_NEEDED = ("dont_know", "manipulation", "asks_clarification")  # cham khong dung dap an chuan
log = logging.getLogger("ai_service.turn_engine")
SESSION_END = "session_end"  # route: phien ket thuc trong luot nay (wrap-up da tra loi, qua han cung), khong hoi them


@dataclass
class TurnContext:
    """Du lieu mot luot di qua 4 buoc. req chi doc; state / plan la ban sao cua luot (perceive tao)."""
    req: NextTurnRequest
    evaluator: Any = None  # None: lay turn_engine.get_evaluator() khi can cham (khong tao Evaluator cho luot 409 / reask)
    collector: Optional[UsageCollector] = None
    retriever: Any = None
    interviewer: Any = None  # ham tra Interviewer (vd get_interviewer), chi node `ask` cua graph goi
    state: Optional[CandidateState] = None
    plan: Optional[InterviewPlan] = None
    topics: Optional[List[Tuple[str, PlanTopic]]] = None
    pos: int = 0
    phase: str = ""
    topic: Optional[PlanTopic] = None
    answer: str = ""
    silent: bool = False
    unclear: bool = False
    key: str = ""
    extra: Any = None
    ev: Optional[Evaluation] = None
    proposal: Any = None
    forced: Optional[Tuple[str, str]] = None
    trace: Optional[DecisionTrace] = None
    result: Optional[TurnResult] = None


def _default_evaluator():
    """Evaluator mac dinh doc tu turn_engine luc goi (test / evals patch `app.turn_engine.get_evaluator`)."""
    from . import turn_engine  # import muon: turn_engine import module nay
    return turn_engine.get_evaluator()


def meta(phase: str, topic_pos: int, total: int, action: str, turn_number: int) -> Dict:
    return {"turn_number": turn_number, "phase": phase, "topic_index": topic_pos, "topic_total": total,
            "action": action}


def perceive_step(ctx: TurnContext) -> str:
    """Doc state, kiem phien / topic / ban ghi voice. Loi 409 / 422 nem ngay (truoc moi ghi chep)."""
    req = ctx.req
    state = ctx.state = req.state.model_copy(deep=True)
    ctx.plan = effective_plan(req.plan, state)  # phase 05: topic da doi (swaps) tai cho; moi reader sau thay plan thuc te
    ctx.topics = check_alignment(state, flat_topics(ctx.plan))
    if state.phase == "done":
        raise ApiError(409, "session_invalid_state", "Phiên đã kết thúc")
    if state.phase == "wrap_up":  # tra loi cau wrap-up xong thi dong phien, khong cham
        state.phase, state.end_reason = "done", state.end_reason or "plan_complete"
        ctx.result = TurnResult(None, None, state, ctx.plan, None, True, {})
        return SESSION_END
    pos = next((i for i, (_, t) in enumerate(ctx.topics) if t.id == state.active_topic_id), None)
    if pos is None:
        raise ApiError(422, "invalid_request", "active_topic_id khong co trong plan")
    ctx.pos, (ctx.phase, ctx.topic) = pos, ctx.topics[pos]
    ctx.answer, ctx.silent, ctx.unclear = heard_answer(req), no_speech(req), low_confidence(req)
    if (ctx.silent or ctx.unclear) and not forced_transition(req.elapsed_seconds, state, ctx.plan, ctx.phase):
        if ctx.silent:
            reject_no_speech()  # 422 voice_no_speech: micro khong thu tieng, state giu nguyen de gui lai cung luot
        if state.counters.stt_reasks < MAX_REASKS:
            return "reask"
        log.info("voice_unclear turn=%d confidence=%s", req.turn_number, req.stt_confidence)
        reject_unclear()  # 422 voice_unclear: state giu nguyen, ung vien go chat roi gui lai cung luot
    return "evaluate"


def reask_step(ctx: TurnContext) -> None:
    """Ban ghi STT kem lan dau trong topic: hoi lai nguyen cau, khong cham, giu do kho va cau trong kho (qa_id)."""
    req, state, topic = ctx.req, ctx.state, ctx.topic
    log.info("voice_reask turn=%d confidence=%s", req.turn_number, req.stt_confidence)
    state.counters.stt_reasks += 1
    state.turn_count += 1
    next(t for t in state.topics if t.id == topic.id).turns.append(req.turn_number + 1)
    # turn_kind giu nguyen (hint van bi tran band, prompt v8 luat 7); action = clarify cho biet day la hoi lai
    info = TurnInfo(turn_number=req.turn_number + 1, phase=ctx.phase, topic_id=topic.id, turn_kind=req.turn_kind,
                    action="clarify", agent_decision="keep_difficulty", difficulty=state.current_difficulty,
                    reasoning="transcript_low_confidence -> clarify (hỏi lại một lần)", qa_id=state.current_qa_id)
    ctx.result = TurnResult(reask_spec(req, ctx.phase, topic, state.current_difficulty), info, state, ctx.plan,
                            unclear_evaluation(req.turn_number), False,
                            meta(ctx.phase, ctx.pos + 1, len(ctx.topics), "clarify", info.turn_number))


async def evaluate_step(ctx: TurnContext) -> None:
    """Cham cau tra loi (RAG + Evaluator); het gio / het luot voi ban ghi kem thi khong cham."""
    req, state = ctx.req, ctx.state
    if ctx.silent or ctx.unclear:  # khong goi RAG / Evaluator, dieu kien uu tien quyet tiep
        ctx.key, ctx.extra, ctx.ev, ctx.proposal = "", TurnChunks(), unclear_evaluation(req.turn_number), None
    else:
        ctx.key, ctx.extra, ctx.ev, ctx.proposal = await evaluate_turn(
            req, state, ctx.phase, ctx.topic, ctx.answer, ctx.evaluator or _default_evaluator(), ctx.collector,
            ctx.retriever, ctx.plan)
    if state.current_qa_id and not ctx.key and not (ctx.silent or ctx.unclear) \
            and ctx.ev.answer_type not in NO_REFERENCE_NEEDED:
        ctx.ev = ctx.ev.model_copy(update={"reference_missing": True})
    record_evaluation(state, ctx.ev, req.turn_number)
    if state.topic_started_s is None:  # state cu: chua biet topic bat dau luc nao
        state.topic_started_s = state.phase_started_s = req.elapsed_seconds


def decide_step(ctx: TurnContext) -> str:
    """Dieu kien uu tien -> (hybrid) de xuat LLM da kiem -> luat. -> SESSION_END hoac hanh dong cua Decision."""
    req, state = ctx.req, ctx.state
    ctx.forced = forced = forced_transition(req.elapsed_seconds, state, ctx.plan, ctx.phase)
    if forced and forced[0] == "end":  # qua han cung: ket thuc ngay, khong hoi them (FR-AI-035)
        state.topics[ctx.pos].status = "done"
        state.phase, state.active_topic_id, state.end_reason = "done", None, forced[1]
        ctx.result = TurnResult(None, None, state, ctx.plan, ctx.ev, True, {})
        return SESSION_END
    ctx.trace = choose_decision(ctx.ev, ctx.proposal, state, ctx.phase, ctx.topic, ctx.topics, ctx.pos, req, forced,
                                ctx.plan)
    if ctx.trace.swap == "applied":  # topic pending da doi tai cho (cung vi tri, cung do dai): tinh lai plan thuc te
        ctx.plan = effective_plan(req.plan, state)
        ctx.topics = flat_topics(ctx.plan)
    return ctx.trace.dec.action


def act_step(ctx: TurnContext) -> None:
    """Ap dung hanh dong vao state, chon cau trong kho, dung QuestionSpec + TurnInfo cho Interviewer."""
    req, state, topics, trace = ctx.req, ctx.state, ctx.topics, ctx.trace
    dec, plan = trace.dec, ctx.plan
    focus = safe_focus(dec.focus)  # chi luu va dung focus da qua kiem (khong giu chuoi nghi injection trong state)
    action, phase_changed, next_pos = apply_action(state, topics, ctx.pos, dec.action, dec.difficulty_delta,
                                                   req.elapsed_seconds, focus)
    n_phase, n_topic = (topics[next_pos] if next_pos is not None else ("wrap_up", None))
    bank = pick(n_topic.bank_questions, state.used_qa_ids, difficulty_bucket(state.current_difficulty)) \
        if action == "ask_main" and n_topic else None
    state.current_qa_id = bank.qa_id if bank else None
    if bank:
        state.used_qa_ids = (state.used_qa_ids + [bank.qa_id])[-30:]
    spec = QuestionSpec(action, n_phase, n_topic, state.current_difficulty, focus=focus,
                        last_question=req.question, last_answer=ctx.answer, phase_changed=phase_changed,
                        asked_on_topic=[t.q for t in req.topic_turns] + [req.question] if action != "ask_main" else [],
                        time_hint=time_hint(req.elapsed_seconds, plan, n_phase), avoid=list(state.asked_questions),
                        bank_question=bank.question if bank else None,
                        reference_answer=hint_source(action, ctx.key, ctx.extra))
    state.turn_count += 1
    if n_topic:
        next(t for t in state.topics if t.id == n_topic.id).turns.append(req.turn_number + 1)
    info = TurnInfo(turn_number=req.turn_number + 1, phase=n_phase, topic_id=n_topic.id if n_topic else None,
                    turn_kind=_KIND[action], action=action, agent_decision=_AGENT.get(action, "switch_topic"),
                    difficulty=state.current_difficulty, reasoning=dec.reasoning, qa_id=state.current_qa_id,
                    decided_by=trace.decided_by, proposed_action=trace.proposed, policy_action=trace.policy,
                    overrule_reason=trace.overrule_reason, action_reason=trace.action_reason,
                    swap_result=trace.swap)
    m = meta(n_phase, (next_pos or 0) + 1 if n_topic else len(topics), len(topics), action, info.turn_number)
    ctx.result = TurnResult(spec, info, state, plan, ctx.ev, False, m)
