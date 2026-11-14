"""Buoc cham mot luot cua next_turn: RAG theo luot (dap an chuan cua cau tu kho hoac chunk) roi Evaluator.

Tach khoi turn_engine (state machine) de moi file gon; turn_engine quyet co cham hay khong (voice kem / im lang thi bo).
"""
import asyncio
import logging
from typing import Optional, Tuple

from .agents.evaluator import EvaluationInput
from .agents.evaluator_provider import Evaluator
from .evaluator_lookup import lookup_for_turn
from .llm.usage import UsageCollector
from .models_interview import CandidateState, Evaluation, NextTurnRequest, PlanTopic, SourceRef
from .plan_snippets import get_retriever, memory_retriever
from .rag.circuit_breaker import MEMORY_ONLY_ERROR
from .source_refs import title_of
from .tracing import observation
from .turn_reference_snippets import TurnChunks, turn_snippets
from .voice_turn import heard_topic_turns, is_voice

ANSWER_KEY_TIMEOUT_S = 2.0  # cache truot -> doc ai_db; qua han thi cham khong co dap an chuan
log = logging.getLogger("ai_service.turn_engine")


async def answer_key(retriever, qa_id: Optional[str], collector: Optional[UsageCollector] = None,
                     cached_only: bool = False) -> str:
    """Dap an chuan cua cau vua hoi neu cau do lay tu kho; RAG tat, loi hay qua han thi chuoi rong (loi, qua han
    ghi vao collector de response bao metadata.rag). cached_only: dang ngat RAG, khong doc ai_db."""
    if not qa_id or retriever is None:
        return ""
    if cached_only:
        return retriever.answers.get(qa_id) or ""
    try:
        return await asyncio.wait_for(retriever.answer_key(qa_id, collector), timeout=ANSWER_KEY_TIMEOUT_S) or ""
    except asyncio.TimeoutError:
        log.warning("answer_key_timeout qa_id=%s", qa_id)
        if collector is not None:
            collector.rag_error("rag_timeout")
        return ""


def reference_source(topic: PlanTopic, qa_id: Optional[str], key: str) -> Optional[SourceRef]:
    """Cau tu kho: tieu de la cau hoi trong plan (khong co thi dong dau dap an); 03b dua vao study_plan."""
    if not key or not qa_id:
        return None
    bank = next((b for b in topic.bank_questions if b.qa_id == qa_id), None)
    return SourceRef(ref=qa_id, title=title_of((bank.question if bank else "") or key),
                     license=bank.license if bank else None)


async def evaluate_turn(req: NextTurnRequest, state: CandidateState, phase: str, topic: PlanTopic, answer: str,
                        evaluator: Evaluator, collector: Optional[UsageCollector],
                        retriever) -> Tuple[str, TurnChunks, Evaluation]:
    """RAG theo luot (dap an chuan hoac chunk) roi Evaluator cham. answer: ban da doi thuat ngu neu la luot voice."""
    live = retriever or get_retriever()
    retriever = live or memory_retriever()  # dang ngat: van con BM25 va cache dap an trong bo nho
    if live is None and retriever is not None and collector is not None:
        collector.rag_error(MEMORY_ONLY_ERROR)
    with observation("rag_turn", "retriever", nest=True, input={"qa_id": state.current_qa_id}) as obs:
        key, extra = await asyncio.gather(  # Phase 02: chi mot trong hai chay (cau kho co dap an chuan thi bo qua)
            answer_key(retriever, state.current_qa_id, collector, cached_only=live is None),
            turn_snippets(retriever, req.track, phase=phase, topic=topic, difficulty=state.current_difficulty,
                          question=req.question, answer=answer, has_answer_key=bool(state.current_qa_id),
                          collector=collector, memory_only=live is None))
        obs.update(output={"answer_key": bool(key), "chunks": [s.ref for s in extra.sources]})
    lookup = lookup_for_turn(retriever, req.track, phase=phase, topic=topic, difficulty=state.current_difficulty,
                             extra=extra, reference_answer=key, evaluator=evaluator)  # None khi EVALUATOR_TOOLS tat (mac dinh)
    # Evaluator nhan ban ghi goc va tu doi thuat ngu (spoken): con giu nguyen van de trich quote
    ev = await evaluator.evaluate(EvaluationInput(
        level=req.level, phase=phase, topic=topic, difficulty=state.current_difficulty, turn_kind=req.turn_kind,
        turn_number=req.turn_number, question=req.question, answer=req.answer, topic_turns=heard_topic_turns(req),
        reference_answer=key, turn_snippets=extra.texts, turn_sources=extra.sources,
        reference_source=reference_source(topic, state.current_qa_id, key), spoken=is_voice(req),
        lookup=lookup), collector)
    return key, extra, ev
