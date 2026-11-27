"""Ket qua mot luot (start / next-turn) va buoc ghi cau hoi da gui vao state sau khi Interviewer stream xong.

Tach khoi turn_engine de turn_steps / turn_graph dung chung ma khong import vong; turn_engine van re-export.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .agents.interviewer import QuestionSpec
from .mock_evaluator import fold
from .models_interview import CandidateState, Evaluation, InterviewPlan, PlanTopic, TurnInfo
from .rag.question_bank import kept_meaning


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
    source: Optional[str] = None  # ai | fallback cua Interviewer (metric TTFT), dien cung luc voi question


def finish_turn(result: TurnResult, question: str, source: str) -> None:
    """Ghi cau hoi da gui vao state (chong lap, FR-AI-038) va nguon cau hoi (ai | fallback)."""
    result.question, result.source = question, source
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


def turn_payload(result: TurnResult, mode: str = "python") -> Dict:
    """Phan `done` cua next-turn tu ket qua luot (tru metadata). mode="json": ban luu trong checkpoint (replay)."""
    return {"evaluation": result.evaluation.model_dump(mode=mode) if result.evaluation else None,
            "question": result.question, "turn": result.turn.model_dump(mode=mode) if result.turn else None,
            "state": result.state.model_dump(mode=mode), "session_end": result.session_end}
