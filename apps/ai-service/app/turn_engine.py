"""Orchestrator MOCK cho start / next-turn: state machine thuan code, Planner/Evaluator/Interviewer gia lap.

Luong moi luot (docs/ai-service/03): Evaluator cham -> cap nhat state -> policy chon action -> Interviewer dien dat.
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .agents.evaluator_provider import Evaluator, get_evaluator
from .api_error import ApiError
from .llm.usage import UsageCollector
from .mock_evaluator import fold
from .agents.interviewer import QuestionSpec, safe_focus
from .agents.planner import get_planner
from .mock_planner import load_track
from .plan_bank_coverage import prefer_covered, settle, start_coverage
from .plan_snippets import attach_reference_snippets, get_retriever
from .models_common import LEVEL_CONFIG
from .models_interview import (CandidateState, Evaluation, InterviewPlan, NextTurnRequest, PlanTopic, StartRequest,
                               TopicState, TurnInfo)
from .rag.difficulty import difficulty_bucket
from .rag.question_bank import kept_meaning, pick
from .state_update import apply_action, record_evaluation
from .tracing import observation
from .time_budget import forced_transition
from .turn_decision import choose_decision, time_hint
from .turn_evaluation import evaluate_turn
from .turn_reference_snippets import TurnChunks
from .voice_turn import MAX_REASKS, heard_answer, low_confidence, no_speech, \
    reask_spec, reject_no_speech, reject_unclear, unclear_evaluation

_KIND = {"ask_main": "main", "follow_up": "follow_up", "hint": "hint", "clarify": "clarify",
         "wrap_up": "main", "end": "main"}  # next_topic / next_phase deu thanh ask_main sau apply_action
_AGENT = {"follow_up": "deepen", "hint": "keep_difficulty", "clarify": "keep_difficulty"}
NO_REFERENCE_NEEDED = ("dont_know", "manipulation", "asks_clarification")  # cham khong dung dap an chuan
log = logging.getLogger("ai_service.turn_engine")


@dataclass
class TurnResult:
    spec: Optional[QuestionSpec]  # None khi phien ket thuc (khong hoi them)
    turn: Optional[TurnInfo]
    state: CandidateState
    plan: InterviewPlan
    evaluation: Optional[Evaluation]
    session_end: bool
    meta: Dict
    question: Optional[str] = None  # dien sau khi Interviewer stream xong (finish_turn)


def finish_turn(result: TurnResult, question: str, source: str) -> None:
    """Ghi cau hoi da gui vao state (chong lap, FR-AI-038) va nguon cau hoi (ai | fallback)."""
    result.question = question
    result.state.asked_questions = (result.state.asked_questions + [_norm(question)])[-30:]
    if result.turn is not None and result.spec is not None and result.spec.fixed_question:
        # hoi lai nguyen cau (ban ghi STT kem): van la cau trong kho neu co, dap an chuan con dung
        result.turn.question_source = "bank" if result.turn.qa_id else source
    elif result.turn is not None:
        # Interviewer dien dat lai cau trong kho (hoac Interviewer loi, dung nguyen van cau trong kho): nguon "bank"
        # Interviewer doi sang y khac thi dap an chuan khong con khop: coi la cau AI tu dat
        bank_q = result.spec.bank_question if result.spec is not None else None
        from_bank = bool(bank_q) and (question == bank_q or (source == "ai" and kept_meaning(bank_q, question)))
        result.turn.question_source = "bank" if from_bank else source
        if not from_bank:
            result.turn.qa_id = result.state.current_qa_id = None  # cau mau thay cau trong kho: khong co dap an chuan


def flat_topics(plan: InterviewPlan) -> List[Tuple[str, PlanTopic]]:
    return [(ph.phase, t) for ph in plan.phases for t in ph.topics]


def _norm(q: str) -> str:
    # 400 ky tu: cat ngan qua lam Jaccard voi cau day du tut duoi 0.8, bo sot cau lap dai
    return re.sub(r"\s+", " ", fold(q)).strip()[:400]


def _meta(phase: str, topic_pos: int, total: int, action: str, turn_number: int) -> Dict:
    return {"turn_number": turn_number, "phase": phase, "topic_index": topic_pos, "topic_total": total,
            "action": action}


async def start_session(req: StartRequest, planner=None, collector: Optional[UsageCollector] = None,
                        retriever=None) -> TurnResult:
    """Planner (LLM hoac mock, co plan du phong) -> doi topic khong co cau trong kho (dem song song voi Planner)
    -> gan reference_snippets (RAG, neu bat) -> cau hoi dau."""
    planner = planner or get_planner()
    catalog = load_track(req.track)
    counting = start_coverage(retriever or get_retriever(), catalog, req.level)
    plan = await planner.plan(req.track, req.level, req.duration_minutes, req.cv_profile, req.jd_profile, collector)
    keep = req.jd_profile.priority_topic_ids() if req.jd_profile else ()
    plan = prefer_covered(plan, catalog, req.level, await settle(counting), keep=keep)
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
    return TurnResult(spec, turn, state, plan, None, False, _meta(first_phase, 1, len(topics), "ask_main", 1))


def _hint_source(action: str, key: str, extra: TurnChunks) -> str:
    """Hint goi y cho dung cau vua hoi: dap an chuan (cau tu kho), khong co thi chunk theo luot cung topic_id."""
    if action != "hint":
        return ""
    return key or extra.hint


def _reask(req: NextTurnRequest, state: CandidateState, plan: InterviewPlan, phase: str, topic: PlanTopic,
           pos: int, total: int) -> TurnResult:
    """Ban ghi STT kem lan dau trong topic: hoi lai nguyen cau, khong cham, giu do kho va cau trong kho (qa_id)."""
    log.info("voice_reask turn=%d confidence=%s", req.turn_number, req.stt_confidence)
    state.counters.stt_reasks += 1
    state.turn_count += 1
    next(t for t in state.topics if t.id == topic.id).turns.append(req.turn_number + 1)
    # turn_kind giu nguyen (hint van bi tran band, prompt v8 luat 7); action = clarify cho biet day la hoi lai
    info = TurnInfo(turn_number=req.turn_number + 1, phase=phase, topic_id=topic.id, turn_kind=req.turn_kind,
                    action="clarify", agent_decision="keep_difficulty", difficulty=state.current_difficulty,
                    reasoning="transcript_low_confidence -> clarify (hỏi lại một lần)", qa_id=state.current_qa_id)
    return TurnResult(reask_spec(req, phase, topic, state.current_difficulty), info, state, plan,
                      unclear_evaluation(req.turn_number), False, _meta(phase, pos + 1, total, "clarify",
                                                                        info.turn_number))


async def next_turn(req: NextTurnRequest, evaluator: Optional[Evaluator] = None,
                    collector: Optional[UsageCollector] = None, retriever=None) -> TurnResult:
    plan, state = req.plan, req.state.model_copy(deep=True)
    topics = flat_topics(plan)
    if state.phase == "done":
        raise ApiError(409, "session_invalid_state", "Phiên đã kết thúc")
    if state.phase == "wrap_up":  # tra loi cau wrap-up xong thi dong phien, khong cham
        state.phase, state.end_reason = "done", state.end_reason or "plan_complete"
        return TurnResult(None, None, state, plan, None, True, {})
    pos = next((i for i, (_, t) in enumerate(topics) if t.id == state.active_topic_id), None)
    if pos is None:
        raise ApiError(422, "invalid_request", "active_topic_id khong co trong plan")
    phase, topic = topics[pos]

    answer, silent, unclear = heard_answer(req), no_speech(req), low_confidence(req)
    if (silent or unclear) and not forced_transition(req.elapsed_seconds, state, plan, phase):
        if silent:
            reject_no_speech()  # 422 voice_no_speech: micro khong thu tieng, state giu nguyen de gui lai cung luot
        if state.counters.stt_reasks < MAX_REASKS:
            return _reask(req, state, plan, phase, topic, pos, len(topics))
        log.info("voice_unclear turn=%d confidence=%s", req.turn_number, req.stt_confidence)
        reject_unclear()  # 422 voice_unclear: state giu nguyen, ung vien go chat roi gui lai cung luot
    if silent or unclear:  # het gio / het luot: khong cham, khong goi RAG / Evaluator, dieu kien uu tien quyet tiep
        key, extra, ev, proposal = "", TurnChunks(), unclear_evaluation(req.turn_number), None
    else:
        key, extra, ev, proposal = await evaluate_turn(req, state, phase, topic, answer, evaluator or get_evaluator(),
                                             collector, retriever)
    if state.current_qa_id and not key and not (silent or unclear) and ev.answer_type not in NO_REFERENCE_NEEDED:
        ev = ev.model_copy(update={"reference_missing": True})
    record_evaluation(state, ev, req.turn_number)
    if state.topic_started_s is None:  # state cu: chua biet topic bat dau luc nao
        state.topic_started_s = state.phase_started_s = req.elapsed_seconds
    forced = forced_transition(req.elapsed_seconds, state, plan, phase)
    if forced and forced[0] == "end":  # qua han cung: ket thuc ngay, khong hoi them (FR-AI-035)
        state.topics[pos].status = "done"
        state.phase, state.active_topic_id, state.end_reason = "done", None, forced[1]
        return TurnResult(None, None, state, plan, ev, True, {})
    trace = choose_decision(ev, proposal, state, phase, topic, topics, pos, req, forced)
    dec = trace.dec

    focus = safe_focus(dec.focus)  # chi luu va dung focus da qua kiem (khong giu chuoi nghi injection trong state)
    action, phase_changed, next_pos = apply_action(state, topics, pos, dec.action, dec.difficulty_delta,
                                                   req.elapsed_seconds, focus)
    n_phase, n_topic = (topics[next_pos] if next_pos is not None else ("wrap_up", None))
    bank = pick(n_topic.bank_questions, state.used_qa_ids, difficulty_bucket(state.current_difficulty)) \
        if action == "ask_main" and n_topic else None
    state.current_qa_id = bank.qa_id if bank else None
    if bank:
        state.used_qa_ids = (state.used_qa_ids + [bank.qa_id])[-30:]
    spec = QuestionSpec(action, n_phase, n_topic, state.current_difficulty, focus=focus,
                        last_question=req.question, last_answer=answer, phase_changed=phase_changed,
                        asked_on_topic=[t.q for t in req.topic_turns] + [req.question] if action != "ask_main" else [],
                        time_hint=time_hint(req.elapsed_seconds, plan, n_phase), avoid=list(state.asked_questions),
                        bank_question=bank.question if bank else None,
                        reference_answer=_hint_source(action, key, extra))
    state.turn_count += 1
    if n_topic:
        next(t for t in state.topics if t.id == n_topic.id).turns.append(req.turn_number + 1)
    info = TurnInfo(turn_number=req.turn_number + 1, phase=n_phase, topic_id=n_topic.id if n_topic else None,
                    turn_kind=_KIND[action], action=action, agent_decision=_AGENT.get(action, "switch_topic"),
                    difficulty=state.current_difficulty, reasoning=dec.reasoning, qa_id=state.current_qa_id,
                    decided_by=trace.decided_by, proposed_action=trace.proposed, policy_action=trace.policy,
                    overrule_reason=trace.overrule_reason, action_reason=trace.action_reason)
    meta = _meta(n_phase, (next_pos or 0) + 1 if n_topic else len(topics), len(topics), action, info.turn_number)
    return TurnResult(spec, info, state, plan, ev, False, meta)

