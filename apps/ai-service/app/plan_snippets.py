"""Gan reference_snippets (FR-AI-022: <= 3 chunk, <= 600 token moi topic) va bank_questions (cau hoi da kiem
chung trong kho, app/rag/question_bank.py) vao plan sau khi plan hop le.

Chi chay mot lan luc start; Evaluator dung lai o cac luot sau, khong tim RAG moi luot. Intro (du an trong CV)
khong co topic_id nen bo qua; scenario khong lay interview_qa, chi textbook theo category chinh cua track
(chi khi RAG_TEXTBOOK_ENABLED=true; kho chua co textbook thi scenario khong co snippet).
"""
import asyncio
import logging
from collections import Counter
from typing import List, Optional

from .catalog.models import TrackCatalog
from .llm.errors import ConfigError
from .llm.usage import UsageCollector
from .models_interview import BankQuestion, InterviewPlan, PlanTopic
from .rag.factory import build_retriever
from .rag.question_bank import plain
from .rag.retriever import Retriever, build_query

log = logging.getLogger("ai_service.rag")
SNIPPET_DEADLINE_S = 5.0  # do 24/10: binh thuong ~0.5 s (topic_id), co viet lai truy van ~2 s
_retriever: Optional[Retriever] = None
_loaded = False


def get_retriever() -> Optional[Retriever]:
    """Retriever dung chung; RAG tat hoac cau hinh sai thi None (phien van chay chi voi key_points)."""
    global _retriever, _loaded
    if not _loaded:
        try:
            _retriever = build_retriever()
        except ConfigError as err:
            log.error("rag_config_error error=%s", err)
        _loaded = True
    return _retriever


def main_category(catalog: TrackCatalog) -> Optional[str]:
    counts = Counter(t.category for t in catalog.topics)
    return counts.most_common(1)[0][0] if counts else None


async def _snippets(retriever: Retriever, phase: str, topic: PlanTopic, catalog: TrackCatalog,
                    collector: Optional[UsageCollector] = None):
    if phase == "intro":
        return []
    query = build_query(None, topic.title, " ".join(topic.key_points))
    if phase == "scenario":
        return await retriever.plan_snippets(topic_id=None, category=main_category(catalog),
                                             difficulty=topic.start_difficulty, query=query, include_qa=False,
                                             collector=collector)
    entry = next((t for t in catalog.topics if t.id == topic.catalog_ref), None)
    return await retriever.plan_snippets(topic_id=topic.catalog_ref, category=entry.category if entry else None,
                                         difficulty=topic.start_difficulty, query=query, collector=collector)


async def _bank(retriever: Retriever, phase: str, topic: PlanTopic, catalog: TrackCatalog) -> List[BankQuestion]:
    """Cau hoi tu kho cho topic ky thuat co catalog_ref (intro la du an trong CV, scenario khong co cau trong kho)."""
    if phase != "technical" or not topic.catalog_ref or not getattr(retriever, "question_bank", True):
        return []  # RAG_QUESTION_BANK=false: Interviewer tu dat cau nhu truoc
    entry = next((t for t in catalog.topics if t.id == topic.catalog_ref), None)
    terms = [topic.title, *topic.key_points, *(entry.key_concepts if entry else [])]
    generic = [catalog.title, catalog.track.replace("_", " "), entry.category if entry else ""]
    entries = await retriever.bank_for_topic(topic.catalog_ref, topic.start_difficulty, terms, generic)
    return [BankQuestion(qa_id=e.qa_id, question=plain(e.question), difficulty=e.difficulty) for e in entries]


async def attach_reference_snippets(plan: InterviewPlan, catalog: TrackCatalog, retriever: Optional[Retriever],
                                    collector: Optional[UsageCollector] = None) -> InterviewPlan:
    """Gan reference_snippets va bank_questions cho moi topic (chay song song, chung mot han)."""
    if retriever is None:
        return plan
    pairs = [(ph, t) for ph in plan.phases for t in ph.topics]
    try:
        # han tong cho RAG luc start: tuy chon, qua han thi plan khong co snippet / cau tu kho (khong cham start)
        results = await asyncio.wait_for(asyncio.gather(
            asyncio.gather(*(_snippets(retriever, ph.phase, t, catalog, collector) for ph, t in pairs)),
            asyncio.gather(*(_bank(retriever, ph.phase, t, catalog) for ph, t in pairs))), timeout=SNIPPET_DEADLINE_S)
    except asyncio.TimeoutError:
        log.warning("rag_snippets_timeout deadline_s=%s", SNIPPET_DEADLINE_S)
        return plan
    out = plan.model_copy(deep=True)
    flat = [t for ph in out.phases for t in ph.topics]
    for topic, snippets, bank in zip(flat, *results):
        topic.reference_snippets = list(snippets)
        topic.bank_questions = bank
    return out
