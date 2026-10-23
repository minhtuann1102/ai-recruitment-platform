"""Truy hoi theo topic (FR-AI-061) va snippet cho plan (FR-AI-022).

Thu tu: interview_qa theo topic_id truoc; duoi MIN_TOPIC_HITS ket qua thi bo sung vector search loc
category + difficulty (ca interview_qa[qa_pair] va textbook). Khu trung theo qa_id, cat theo ngan sach token.
RAG la tuy chon: loi DB hay embedding chi ghi log va tra rong, buoi phong van khong chet.
"""
import logging
import math
from typing import Awaitable, Callable, List, Optional, Protocol, Sequence

from .difficulty import difficulty_bucket
from .models import Chunk, SearchFilters

log = logging.getLogger("ai_service.rag")

MIN_TOPIC_HITS = 2
OVERFETCH = 4  # lay du roi khu trung, de question va qa_pair cung cap khong chiem hai cho
MIN_TAIL_TOKENS = 50  # phan con lai nho hon thi khong cat chunk cuoi nua

EmbedFn = Callable[[str], Awaitable[List[float]]]


class KnowledgeRepository(Protocol):
    async def list_by_topic_id(self, topic_id: str, difficulty: Optional[str], limit: int) -> List[Chunk]: ...
    async def search(self, vector: Sequence[float], filters: SearchFilters, limit: int) -> List[Chunk]: ...
    async def get_pair_by_qa_id(self, qa_id: str) -> Optional[Chunk]: ...


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


def build_query(category: Optional[str], title: str, extra: str = "") -> str:
    """rag-design muc 4: category + topic + tom tat ngan; khong dua ca lich su vao query."""
    return " | ".join(p for p in (category, title, extra.strip()[:300]) if p)


class Retriever:
    def __init__(self, repo: KnowledgeRepository, embed: EmbedFn, *, k: int = 5, token_budget: int = 1500):
        self._repo, self._embed, self.k, self.token_budget = repo, embed, k, token_budget

    async def retrieve_for_topic(self, *, topic_id: Optional[str], category: Optional[str], difficulty: int,
                                 query: str, include_qa: bool = True, k: Optional[int] = None,
                                 token_budget: Optional[int] = None, chunk_type: str = "qa_pair") -> List[Chunk]:
        """chunk_type cua interview_qa trong vector fallback: qa_pair (Planner, Evaluator) hoac question
        (Interviewer tim cau hoi tuong tu, rag-design muc 4)."""
        k, budget = k or self.k, token_budget or self.token_budget
        via = "topic"
        try:
            bucket = difficulty_bucket(difficulty)
            found = await self._repo.list_by_topic_id(topic_id, bucket, k) if include_qa and topic_id else []
            found = dedup(found)
            if len(found) < MIN_TOPIC_HITS:
                via = "topic+vector" if found else "vector"
                types = ("interview_qa", "textbook") if include_qa else ("textbook",)
                vector = await self._embed(query)
                hits = await self._repo.search(vector, SearchFilters(types, category, bucket, chunk_type),
                                               k * OVERFETCH)
                found = dedup([*found, *hits])
        except Exception as err:  # RAG tuy chon (FR-AI-022): khong de loi DB/embedding lam hong phien
            log.warning("rag_retrieve_failed topic=%s error=%s", topic_id, type(err).__name__)
            return []
        result = trim_to_budget(found[:k], budget)
        # NFR-AI-OBS04: log id + diem, khong log noi dung
        log.info("rag_retrieve topic=%s via=%s hits=%s", topic_id, via,
                 " ".join(f"{c.dedup_key}:{'-' if c.score is None else f'{c.score:.3f}'}" for c in result))
        return result

    async def plan_snippets(self, *, topic_id: Optional[str], category: Optional[str], difficulty: int,
                            query: str, include_qa: bool = True) -> List[str]:
        """FR-AI-022: toi da 3 chunk, <= 600 token moi topic, luu vao PlanTopic.reference_snippets."""
        chunks = await self.retrieve_for_topic(topic_id=topic_id, category=category, difficulty=difficulty,
                                               query=query, include_qa=include_qa, k=3, token_budget=600)
        return [c.content for c in chunks]

    async def reference_answer(self, qa_id: str) -> Optional[Chunk]:
        """Evaluator: cau hoi tu ngan hang thi tra thang theo qa_id, khong tim tuong dong (rag-design muc 4)."""
        try:
            return await self._repo.get_pair_by_qa_id(qa_id)
        except Exception as err:
            log.warning("rag_reference_failed qa_id=%s error=%s", qa_id, type(err).__name__)
            return None
