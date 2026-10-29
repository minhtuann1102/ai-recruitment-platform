"""Gan reference_snippets (FR-AI-022: <= 3 chunk, <= 600 token moi topic) va bank_questions (cau hoi da kiem
chung trong kho, app/rag/question_bank.py) vao plan sau khi plan hop le.

Chi chay mot lan luc start; Evaluator dung lai o cac luot sau, khong tim RAG moi luot. Intro (du an trong CV)
khong co topic_id nen bo qua; scenario khong lay interview_qa, chi textbook theo category chinh cua track
(chi khi RAG_TEXTBOOK_ENABLED=true; kho chua co textbook thi scenario khong co snippet).
"""
import asyncio
import logging
from collections import Counter
from typing import Dict, List, Optional

from .catalog.models import TrackCatalog
from .llm.errors import ConfigError
from .llm.usage import UsageCollector
from .models_interview import BankQuestion, InterviewPlan, PlanTopic
from .rag.circuit_breaker import SOFT_ERRORS, CircuitBreaker
from .rag.factory import build_retriever
from .rag.question_bank import plain
from .rag.retriever import Retriever, build_query
from .rag.settings import load_rag_settings

log = logging.getLogger("ai_service.rag")
SNIPPET_DEADLINE_S = 5.0  # do 24/10: binh thuong ~0.5 s (topic_id), co viet lai truy van ~2 s
_retriever: Optional[Retriever] = None
_config_error: Optional[str] = None  # RAG bat nhung cau hinh sai: moi response bao loi nay trong metadata.rag
_breaker = CircuitBreaker(60)  # thay bang RAG_COOLDOWN_S khi nap cau hinh
_loaded = False
RAG_ERROR_MESSAGE = "RAG lỗi, lượt này chạy không có dữ liệu tham chiếu từ kho"
RAG_DEGRADED_MESSAGE = ("Một phần RAG lỗi (tìm từ khóa, vector hoặc truy hồi theo lượt), "
                        "kết quả lấy từ phần còn chạy được")


def _load() -> None:
    global _retriever, _config_error, _breaker, _loaded
    if _loaded:
        return
    try:
        settings = load_rag_settings()
        _breaker = CircuitBreaker(settings.cooldown_s)
        _retriever = build_retriever(settings)
    except ConfigError as err:
        _config_error = str(err)
        log.error("rag_config_error error=%s", err)
    _loaded = True


def get_retriever() -> Optional[Retriever]:
    """Retriever dung chung; RAG tat, cau hinh sai hoac dang ngat tam (vua loi) thi None (phien van chay chi voi
    key_points)."""
    _load()
    return None if _breaker.is_open() else _retriever


async def warm_rag() -> None:
    """Luc khoi dong: nap corpus BM25 truoc (chay nen) de /api/start dau tien khong phai cho. Loi chi ghi log;
    hybrid tu lui ve vector va bao degraded cho toi khi nap duoc."""
    retriever = get_retriever()
    if retriever is None or getattr(retriever, "hybrid", None) is None:
        return
    try:
        await retriever.hybrid.bm25.index()
    except Exception as err:
        log.warning("rag_warm_failed error=%s", type(err).__name__)


async def close_rag() -> None:
    """Luc tat service: dong pool ket noi ai_db."""
    close = getattr(getattr(_retriever, "_repo", None), "close", None)
    if close is not None:
        try:
            await close()
        except Exception as err:
            log.warning("rag_close_failed error=%s", type(err).__name__)


def note_rag_errors(collector: Optional[UsageCollector]) -> None:
    """Cuoi request: co loi RAG thi ngat RAG tam thoi (RAG_COOLDOWN_S) cho cac request sau."""
    if collector is not None and collector.rag_errors:
        _breaker.trip(collector.rag_errors)


def rag_status(collector: Optional[UsageCollector] = None) -> Dict:
    """metadata.rag (start, next-turn) va /api/health: on | off (RAG_ENABLED=false) | degraded (mot duong hybrid
    loi, van co ket qua) | error (cau hinh sai, dang
    ngat tam sau loi, hoac ai_db loi / qua han trong request nay; phien van chay tiep khong co RAG). Khong chua noi
    dung hay URL ket noi."""
    _load()
    if _config_error:
        return {"status": "error", "errors": ["rag_config_error"], "message": f"RAG đã tắt: {_config_error}"}
    if _retriever is None:
        return {"status": "off"}
    errors = list(collector.rag_errors) if collector is not None else []
    if any(e not in SOFT_ERRORS for e in errors):
        return {"status": "error", "errors": errors, "message": RAG_ERROR_MESSAGE}
    if errors:  # chi loi nhe (mot duong hybrid): van co RAG, khong them fallback rag_unavailable
        return {"status": "degraded", "errors": errors, "message": RAG_DEGRADED_MESSAGE}
    if _breaker.is_open():
        return {"status": "error", "errors": ["rag_cooldown"], "last_errors": _breaker.last_errors,
                "message": f"RAG tạm tắt sau lỗi ai_db, thử lại sau {_breaker.remaining_s()} s"}
    return {"status": "on"}


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


async def _bank(retriever: Retriever, phase: str, topic: PlanTopic, catalog: TrackCatalog,
                collector: Optional[UsageCollector] = None) -> List[BankQuestion]:
    """Cau hoi tu kho cho topic ky thuat co catalog_ref (intro la du an trong CV, scenario khong co cau trong kho)."""
    if phase != "technical" or not topic.catalog_ref or not getattr(retriever, "question_bank", True):
        return []  # RAG_QUESTION_BANK=false: Interviewer tu dat cau nhu truoc
    entry = next((t for t in catalog.topics if t.id == topic.catalog_ref), None)
    terms = [topic.title, *topic.key_points, *(entry.key_concepts if entry else [])]
    generic = [catalog.title, catalog.track.replace("_", " "), entry.category if entry else ""]
    query = build_query(None, topic.title, " ".join(topic.key_points))  # cung truy van voi snippet: dung chung vector
    entries = await retriever.bank_for_topic(topic.catalog_ref, topic.start_difficulty, terms, generic,
                                             collector=collector, query=query)
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
            asyncio.gather(*(_bank(retriever, ph.phase, t, catalog, collector) for ph, t in pairs))),
            timeout=SNIPPET_DEADLINE_S)
    except asyncio.TimeoutError:
        log.warning("rag_snippets_timeout deadline_s=%s", SNIPPET_DEADLINE_S)
        if collector is not None:
            collector.rag_error("rag_timeout")
        return plan
    out = plan.model_copy(deep=True)
    flat = [t for ph in out.phases for t in ph.topics]
    for topic, snippets, bank in zip(flat, *results):
        topic.reference_snippets = list(snippets)
        topic.bank_questions = bank
    return out
