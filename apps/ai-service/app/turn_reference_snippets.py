"""Truy hoi theo luot (plans/261029-1415-hybrid-grounded-rag, Phase 02): moi next-turn tim them chunk theo chinh cau
vua hoi + cau tra loi, bo sung cho reference_snippets co dinh cua topic (gan luc start).

Chi BM25 trong bo nho (Phase 01) + tang diem theo topic_id, gop RRF; khong viet lai, khong embed: do 29/10 viet lai +
embed mat 2.2-3.8 s, con TTFT P95 da sat moc 6 s. BM25 chay ngay; SQL topic_id co han TURN_DEADLINE_S, loi hay qua
han thi van tra ket qua BM25 (khong tang diem) va bao `rag_turn_failed` (loi nhe: degraded, khong ngat RAG).
Bo qua khi: RAG / hybrid / RAG_TURN_RETRIEVAL tat, phase intro, cau co qa_id (da co dap an chuan), corpus chua nap.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .catalog.models import TrackCatalog
from .mock_planner import load_track
from .llm.usage import UsageCollector
from .models_interview import PlanTopic, SourceRef
from .plan_snippets import main_category
from .rag.difficulty import difficulty_bucket
from .rag.hybrid_fusion import rrf
from .rag.models import Chunk, SearchFilters
from .rag.retriever import OVERFETCH, Retriever, dedup, trim_to_budget
from .source_refs import source_ref

log = logging.getLogger("ai_service.rag")
TURN_DEADLINE_S = 1.0  # BM25 < 20 ms; con lai la SQL topic_id (~0.25 s qua pool), chay cung luc voi dap an chuan
TURN_ERROR = "rag_turn_failed"
TOPIC_BOOST = 0.5  # topic_id chi tang diem chunk BM25 da tim thay, khong tu them chunk (snippet topic da co)
ANSWER_CHARS = 800  # cau tra loi lan man dai: chi lay phan dau lam truy van, giam bat nham theo tu chung
TURN_K, TURN_TOKENS = 3, 600  # cung gioi han voi snippet cua topic (FR-AI-022)
SQL_COOLDOWN_S = 30.0  # SQL topic_id loi / qua han: cac luot sau chi dung BM25, khong moi luot cho them 1 s
_sql_off_until = 0.0


@dataclass
class TurnChunks:
    texts: List[str] = field(default_factory=list)
    # nguon hint khi khong co dap an chuan: chi chunk cung topic_id voi topic dang hoi (BM25 thuan co the bat nham
    # theo tu chung, cau tra loi sai keo truy van lech sang khai niem khac)
    hint: str = ""
    sources: List[SourceRef] = field(default_factory=list)  # cung thu tu texts (03b)


def _known(content: str, known: Sequence[str]) -> bool:
    """Trung snippet cua topic, ke ca snippet cuoi bi trim_to_budget cat va them " ..."."""
    return any(content == k or (k.endswith(" ...") and content.startswith(k[:-4])) for k in known)


def _swallow(task: asyncio.Future) -> None:
    if not task.cancelled():
        task.exception()


def _filters(retriever: Retriever, phase: str, topic: PlanTopic, catalog: TrackCatalog) -> Optional[SearchFilters]:
    textbook = ("textbook",) if retriever.textbook else ()
    if phase == "scenario":  # nhu luc start: scenario khong lay interview_qa
        return SearchFilters(textbook, main_category(catalog)) if textbook else None
    entry = next((t for t in catalog.topics if t.id == topic.catalog_ref), None)
    return SearchFilters(("interview_qa", *textbook), entry.category if entry else None)


async def _topic_list(retriever: Retriever, topic: PlanTopic, bucket: Optional[str],
                      collector: Optional[UsageCollector]) -> List[Chunk]:
    global _sql_off_until
    if time.monotonic() < _sql_off_until:
        err_name = "cooldown"
    else:
        task = asyncio.ensure_future(retriever.repo.list_by_topic_id(topic.catalog_ref, bucket, TURN_K * OVERFETCH))
        try:
            # shield: huy truy van psycopg phai cho server xac nhan (toi 5 s, lau hon neu mang treo); de no chay
            # tiep o nen (giu 1 ket noi pool toi statement_timeout) thay vi giu luot qua han
            return await asyncio.wait_for(asyncio.shield(task), TURN_DEADLINE_S)
        except Exception as err:  # gom ca TimeoutError: chi mat phan tang diem, van dung ket qua BM25
            task.add_done_callback(_swallow)
            _sql_off_until = time.monotonic() + SQL_COOLDOWN_S
            err_name = type(err).__name__
    log.warning("rag_turn_failed topic=%s error=%s", topic.catalog_ref, err_name)
    if collector is not None:
        collector.rag_error(TURN_ERROR)
    return []


async def _search(retriever: Retriever, filters: SearchFilters, topic: PlanTopic, difficulty: int, query: str,
                  known: Sequence[str], collector: Optional[UsageCollector]) -> List[Chunk]:
    index = retriever.hybrid.bm25.ready()
    if index is None:  # corpus chua nap xong (vua khoi dong): khong cho
        log.info("rag_turn_skipped reason=corpus_not_loaded")
        return []
    bucket = difficulty_bucket(difficulty)
    filters = SearchFilters(filters.source_types, filters.category, bucket)
    lexical = index.search(query, filters, TURN_K * OVERFETCH)
    if not lexical:
        return []
    by_topic: List[Chunk] = []
    if topic.catalog_ref and "interview_qa" in filters.source_types:
        by_topic = await _topic_list(retriever, topic, bucket, collector)
    found = {c.dedup_key for c in lexical}
    fused = [c for c in rrf([lexical, by_topic], [1.0, TOPIC_BOOST])
             if c.dedup_key in found and not _known(c.content, known)]
    return trim_to_budget(dedup(fused)[:TURN_K], TURN_TOKENS)


async def turn_snippets(retriever: Optional[Retriever], track: str, *, phase: str, topic: PlanTopic,
                        difficulty: int, question: str, answer: str, has_answer_key: bool,
                        collector: Optional[UsageCollector] = None) -> TurnChunks:
    """Chunk theo luot (<= 3, <= 600 token), khong trung snippet cua topic; rong khi bo qua, loi hay qua han."""
    if (getattr(retriever, "hybrid", None) is None or not getattr(retriever, "turn_retrieval", False)
            or phase == "intro" or has_answer_key or not 1 <= difficulty <= 5):  # do kho ngoai 1-5: state hong
        return TurnChunks()
    query = f"{question}\n{answer[:ANSWER_CHARS]}"
    try:
        filters = _filters(retriever, phase, topic, load_track(track))
        if filters is None:
            return TurnChunks()
        chunks = await _search(retriever, filters, topic, difficulty, query, topic.reference_snippets, collector)
    except Exception as err:  # tuy chon: loi bat ngo thi luot van cham voi snippet cua topic
        log.warning("rag_turn_failed topic=%s error=%s", topic.catalog_ref, type(err).__name__)
        if collector is not None:
            collector.rag_error(TURN_ERROR)
        return TurnChunks()
    # NFR-AI-OBS04: log id + diem, khong log noi dung
    log.info("rag_turn topic=%s hits=%s", topic.catalog_ref,
             " ".join(f"{c.dedup_key}:{'-' if c.score is None else f'{c.score:.4f}'}" for c in chunks))
    hint = next((c.content for c in chunks if topic.catalog_ref and c.topic_id == topic.catalog_ref), "")
    return TurnChunks([c.content for c in chunks], hint, [source_ref(c) for c in chunks])
