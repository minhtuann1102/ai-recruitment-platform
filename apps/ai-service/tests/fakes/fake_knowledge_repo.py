"""Kho knowledge_chunks gia trong bo nho, CHI de kiem logic retriever (thu tu, fallback, khu trung, ngan sach)."""
from typing import List, Optional, Sequence

from app.rag.models import Chunk, SearchFilters


def qa(qa_id: str, topic_id: str, content: str = "Q?\n\nA.", difficulty: str = "medium",
       chunk_type: str = "qa_pair", score: Optional[float] = None, category: str = "Backend") -> Chunk:
    return Chunk(id=f"{qa_id}-{chunk_type}", content=content, source_type="interview_qa", topic_id=topic_id,
                 category=category, difficulty=difficulty, qa_id=qa_id, chunk_type=chunk_type, score=score)


def textbook(cid: str, content: str = "Node.js > Streams\nBackpressure ...", score: float = 0.5) -> Chunk:
    return Chunk(id=cid, content=content, source_type="textbook", topic_id=None, category="Backend",
                 difficulty=None, qa_id=None, chunk_type=None, score=score)


class FakeKnowledgeRepo:
    def __init__(self, by_topic: Sequence[Chunk] = (), hits: Sequence[Chunk] = (), fail: Exception = None):
        self.by_topic, self.hits, self.fail = list(by_topic), list(hits), fail
        self.calls: List[tuple] = []

    async def list_by_topic_id(self, topic_id: str, difficulty: Optional[str], limit: int) -> List[Chunk]:
        self.calls.append(("topic", topic_id, difficulty, limit))
        if self.fail:
            raise self.fail
        return [c for c in self.by_topic if c.topic_id == topic_id][:limit]

    async def search(self, vector: Sequence[float], filters: SearchFilters, limit: int) -> List[Chunk]:
        self.calls.append(("search", filters, limit))
        if self.fail:
            raise self.fail
        return [c for c in self.hits if c.source_type in filters.source_types][:limit]

    async def get_pair_by_qa_id(self, qa_id: str) -> Optional[Chunk]:
        self.calls.append(("pair", qa_id))
        if self.fail:
            raise self.fail
        return next((c for c in self.by_topic + self.hits if c.qa_id == qa_id and c.chunk_type == "qa_pair"), None)


class FakeEmbed:
    def __init__(self, fail: Exception = None):
        self.queries: List[str] = []
        self.fail = fail

    async def __call__(self, text: str, collector=None) -> List[float]:
        self.queries.append(text)
        if self.fail:
            raise self.fail
        return [0.1] * 1536
