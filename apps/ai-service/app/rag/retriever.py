"""Truy hoi theo topic (FR-AI-061) va snippet cho plan (FR-AI-022).

Thu tu: interview_qa theo topic_id truoc; duoi MIN_TOPIC_HITS ket qua thi bo sung vector search loc
category + difficulty (ca interview_qa[qa_pair] va textbook). Khu trung theo qa_id, cat theo ngan sach token.
RAG la tuy chon: loi DB hay embedding ghi log, ghi ma loi vao collector (bao ve trong metadata.rag) va tra rong,
buoi phong van khong chet.
"""
import logging
import math
from typing import Awaitable, Callable, List, Optional, Protocol, Sequence, Tuple

from .difficulty import difficulty_bucket
from ..llm.usage import UsageCollector
from .models import Chunk, SearchFilters
from .query_expansion import expand_query
from .hybrid_search import PARTIAL_ERROR, HybridSearcher
from .question_bank import AnswerCache, BankEntry, rank

log = logging.getLogger("ai_service.rag")

MIN_TOPIC_HITS = 2
OVERFETCH = 4  # lay du roi khu trung, de question va qa_pair cung cap khong chiem hai cho
MIN_TAIL_TOKENS = 50
BANK_FETCH = 80  # so cap Q&A lay moi topic de loc + xep (p90 ~110 cau/topic), giu toi da 3 cau trong plan  # phan con lai nho hon thi khong cat chunk cuoi nua

EmbedFn = Callable[..., Awaitable[List[float]]]  # embed(text, collector=None)
RewriteFn = Callable[..., Awaitable[str]]  # rewrite(query, collector) -> truy van tieng Anh


class KnowledgeRepository(Protocol):
    async def list_by_topic_id(self, topic_id: str, difficulty: Optional[str], limit: int) -> List[Chunk]: ...
    async def search(self, vector: Sequence[float], filters: SearchFilters, limit: int) -> List[Chunk]: ...
    async def get_pair_by_qa_id(self, qa_id: str) -> Optional[Chunk]: ...
    async def list_bank(self, topic_id: str, difficulty: Optional[str], limit: int) -> List[BankEntry]: ...


def estimate_tokens(text: str) -> int:
    """Uoc luong than trong: ~3 ky tu/token (tieng Viet co dau ton token hon tieng Anh). Khong can tokenizer."""
    return math.ceil(len(text) / 3)


def dedup(chunks: Sequence[Chunk]) -> List[Chunk]:
    seen, out = set(), []
    for c in chunks:
        if c.dedup_key not in seen:
            seen.add(c.dedup_key)
            out.append(c)
    return out


def trim_to_budget(chunks: Sequence[Chunk], budget: int) -> List[Chunk]:
    out, used = [], 0
    for c in chunks:
        cost = estimate_tokens(c.content)
        if used + cost <= budget:
            out.append(c)
            used += cost
            continue
        remaining = budget - used
        if remaining >= MIN_TAIL_TOKENS:
            # -6 ky tu de ca hau to " ..." van nam trong ngan sach
            out.append(Chunk(**{**c.__dict__, "content": c.content[: remaining * 3 - 6].rstrip() + " ..."}))
        break
    return out


def _record(collector: Optional[UsageCollector], code: str) -> None:
    if collector is not None:
        collector.rag_error(code)


def build_query(category: Optional[str], title: str, extra: str = "") -> str:
    """rag-design muc 4: category + topic + tom tat ngan; khong dua ca lich su vao query."""
    return " | ".join(p for p in (category, title, extra.strip()[:300]) if p)


class Retriever:
    def __init__(self, repo: KnowledgeRepository, embed: EmbedFn, *, k: int = 5, token_budget: int = 1500,
                 textbook: bool = False, rewrite: Optional[RewriteFn] = None, question_bank: bool = True,
                 hybrid: bool = False):
        """textbook=False (mac dinh, RAG_TEXTBOOK_ENABLED): kho chua co textbook nen khong tim (do 24/10: tim
        textbook cho scenario ton ~1.5 s ma luon rong). rewrite: LLM viet lai truy van sang tieng Anh cho duong
        vector (RAG_QUERY_REWRITE); do 24/10 tren 32 truy van thuan Viet: recall@5 0.594 -> 0.938."""
        self._repo, self._embed, self.k, self.token_budget = repo, embed, k, token_budget
        self.textbook, self._rewrite = textbook, rewrite
        self.answers, self.question_bank = AnswerCache(), question_bank
        # hybrid (RAG_HYBRID, mac dinh bat qua factory): tu khoa + vector + topic_id gop RRF; False: duong cu
        # (topic_id truoc, vector khi < MIN_TOPIC_HITS), giu de so sanh truoc/sau
        self.hybrid = HybridSearcher(repo, embed, self._search_text) if hybrid else None

    async def search_text(self, query: str, collector: Optional[UsageCollector] = None) -> str:
        """Van ban dem embed: truy van goc + ban tieng Anh do LLM viet lai; khong co hoac loi thi dung tu dien."""
        return (await self._search_text(query, collector))[0]

    async def _search_text(self, query: str, collector: Optional[UsageCollector] = None) -> Tuple[str, bool]:
        """(van ban, cache duoc): viet lai tra nguyen truy van (loi LLM hoac khong doi) thi khong cache."""
        if self._rewrite is not None:
            english = await self._rewrite(query, collector)
            if english and english.strip() != query.strip():
                return f"{query}\n{english}", True
            return expand_query(query), False
        return expand_query(query), True

    async def retrieve_for_topic(self, *, topic_id: Optional[str], category: Optional[str], difficulty: int,
                                 query: str, include_qa: bool = True, k: Optional[int] = None,
                                 token_budget: Optional[int] = None, chunk_type: str = "qa_pair",
                                 collector: Optional[UsageCollector] = None) -> List[Chunk]:
        """chunk_type cua interview_qa trong vector fallback: qa_pair (Planner, Evaluator) hoac question
        (Interviewer tim cau hoi tuong tu, rag-design muc 4)."""
        k, budget = k or self.k, token_budget or self.token_budget
        types = (("interview_qa",) if include_qa else ()) + (("textbook",) if self.textbook else ())
        if not types:  # vd scenario khi chua bat textbook: khong co gi de tim, khong ton embed
            return []
        via = "topic"
        try:
            bucket = difficulty_bucket(difficulty)
            if self.hybrid is not None:
                via = "hybrid"
                by_topic = include_qa and topic_id
                extra = [self._repo.list_by_topic_id(topic_id, bucket, k * OVERFETCH)] if by_topic else []
                found = await self.hybrid.search(query, SearchFilters(types, category, bucket, chunk_type),
                                                 k * OVERFETCH, collector, extra)
                return self._finish(topic_id, via, found, k, budget)
            found = await self._repo.list_by_topic_id(topic_id, bucket, k) if include_qa and topic_id else []
            found = dedup(found)
            if len(found) < MIN_TOPIC_HITS:
                via = "topic+vector" if found else "vector"
                vector = await self._embed(await self.search_text(query, collector), collector=collector)
                hits = await self._repo.search(vector, SearchFilters(types, category, bucket, chunk_type),
                                               k * OVERFETCH)
                found = dedup([*found, *hits])
        except Exception as err:  # RAG tuy chon (FR-AI-022): khong de loi DB/embedding lam hong phien
            log.warning("rag_retrieve_failed topic=%s error=%s", topic_id, type(err).__name__)
            _record(collector, "rag_retrieve_failed")
            return []
        return self._finish(topic_id, via, found, k, budget)

    @staticmethod
    def _finish(topic_id: Optional[str], via: str, found: Sequence[Chunk], k: int, budget: int) -> List[Chunk]:
        result = trim_to_budget(found[:k], budget)
        # NFR-AI-OBS04: log id + diem, khong log noi dung
        log.info("rag_retrieve topic=%s via=%s hits=%s", topic_id, via,
                 " ".join(f"{c.dedup_key}:{'-' if c.score is None else f'{c.score:.3f}'}" for c in result))
        return result

    async def plan_snippets(self, *, topic_id: Optional[str], category: Optional[str], difficulty: int,
                            query: str, include_qa: bool = True,
                            collector: Optional[UsageCollector] = None) -> List[str]:
        """FR-AI-022: toi da 3 chunk, <= 600 token moi topic, luu vao PlanTopic.reference_snippets."""
        chunks = await self.retrieve_for_topic(topic_id=topic_id, category=category, difficulty=difficulty,
                                               query=query, include_qa=include_qa, k=3, token_budget=600,
                                               collector=collector)
        return [c.content for c in chunks]

    async def reference_answer(self, qa_id: str, collector: Optional[UsageCollector] = None) -> Optional[Chunk]:
        """Evaluator: cau hoi tu ngan hang thi tra thang theo qa_id, khong tim tuong dong (rag-design muc 4)."""
        try:
            return await self._repo.get_pair_by_qa_id(qa_id)
        except Exception as err:
            log.warning("rag_reference_failed qa_id=%s error=%s", qa_id, type(err).__name__)
            _record(collector, "rag_reference_failed")
            return None

    async def bank_for_topic(self, topic_id: str, difficulty: int, topic_terms: Sequence[str],
                             generic: Sequence[str] = (), n: int = 3,
                             collector: Optional[UsageCollector] = None, query: str = "") -> List[BankEntry]:
        """Cau hoi tu kho cho topic (question_bank.rank); dap an vao cache cho Evaluator. Loi thi tra rong.
        Hybrid + co query: xep hang them theo do giong vector cua cau hoi voi truy van topic (cung vector voi
        snippet, khong embed lai); embed loi thi chi xep theo tu trung."""
        bucket = difficulty_bucket(difficulty)
        vector = await self._bank_vector(query, collector)
        try:
            entries = await (self._repo.list_bank(topic_id, bucket, BANK_FETCH, vector) if vector is not None
                             else self._repo.list_bank(topic_id, bucket, BANK_FETCH))
        except Exception as err:
            log.warning("rag_bank_failed topic=%s error=%s", topic_id, type(err).__name__)
            _record(collector, "rag_bank_failed")
            return []
        chosen = rank(entries, topic_terms, bucket, n, generic)
        for e in chosen:
            self.answers.put(e.qa_id, e.pair)
        log.info("rag_bank topic=%s fetched=%d chosen=%s", topic_id, len(entries), " ".join(e.qa_id for e in chosen))
        return chosen

    async def _bank_vector(self, query: str, collector: Optional[UsageCollector]) -> Optional[List[float]]:
        if self.hybrid is None or not query:
            return None
        try:
            return await self.hybrid.query_vector(query, collector)
        except Exception as err:
            log.warning("rag_bank_vector_failed error=%s", type(err).__name__)
            _record(collector, PARTIAL_ERROR)
            return None

    async def answer_key(self, qa_id: str, collector: Optional[UsageCollector] = None) -> Optional[str]:
        """Dap an chuan (cap Q&A) theo qa_id: cache truoc, truot thi doc ai_db; loi thi None (cham khong co dap an)."""
        cached = self.answers.get(qa_id)
        if cached is not None:
            return cached
        chunk = await self.reference_answer(qa_id, collector)
        if chunk is None:
            return None
        self.answers.put(qa_id, chunk.content)
        return self.answers.get(qa_id)
