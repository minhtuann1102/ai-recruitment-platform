"""Tao Retriever theo cau hinh. RAG_ENABLED=false thi tra None: agent chay chi voi key_points."""
from typing import List, Optional

from ..llm.gateway import LlmGateway, get_gateway
from ..llm.usage import UsageCollector
from .repository import PgKnowledgeRepository
from .retriever import Retriever
from .settings import RagSettings, load_rag_settings


def build_retriever(settings: Optional[RagSettings] = None,
                    gateway: Optional[LlmGateway] = None) -> Optional[Retriever]:
    settings = settings or load_rag_settings()
    if not settings.enabled:
        return None
    gw = gateway or get_gateway()

    async def embed_query(text: str, collector: Optional[UsageCollector] = None) -> List[float]:
        # embed bang dung model luu trong kho (contract: loc embedding_model + cung model cho query);
        # collector: ghi token embedding vao metadata cua request (FR-AI-080)
        return (await gw.embed([text], collector=collector))[0]

    return Retriever(PgKnowledgeRepository(settings), embed_query, textbook=settings.textbook_enabled)
