"""Kieu du lieu chung cua duong doc RAG."""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Chunk:
    id: str
    content: str
    source_type: str  # interview_qa | textbook
    topic_id: Optional[str]
    category: Optional[str]
    difficulty: Optional[str]
    qa_id: Optional[str]
    chunk_type: Optional[str]  # question | qa_pair (interview_qa); textbook tuy pipeline
    score: Optional[float] = None  # cosine similarity; None khi lay theo topic_id (khong qua tim tuong dong)
    source_url: Optional[str] = None  # metadata.source_url cua DE (Phase 03b: tai lieu trong study_plan)

    @property
    def dedup_key(self) -> str:
        """question va qa_pair cung qa_id tinh la mot (rag-design muc 4)."""
        return self.qa_id or self.id


@dataclass(frozen=True)
class SearchFilters:
    source_types: Tuple[str, ...] = ("interview_qa", "textbook")
    category: Optional[str] = None
    difficulty: Optional[str] = None  # ban ghi difficulty NULL (textbook) van khop
    chunk_type: Optional[str] = None  # chi ap cho interview_qa
