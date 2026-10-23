"""Goi API embedding OpenAI-compatible (FR-011, FR-015).

Retry gioi han nam o SDK (max_retries); loi con lai de cho nguoi goi dem theo batch, khong lam
mat ban ghi da ghi thanh cong.
"""
from typing import List, Protocol, Sequence

from openai import OpenAI

from .settings import ConfigError, IndexSettings

BATCH_SIZE = 100


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> List[List[float]]: ...


class EmbeddingClient:
    def __init__(self, settings: IndexSettings):
        self._client = OpenAI(base_url=settings.base_url, api_key=settings.api_key, max_retries=3, timeout=60)
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        response = self._client.embeddings.create(model=self._model, input=list(texts))
        return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]

    def probe(self) -> None:
        """Embed thu 1 chuoi: kiem provider phuc vu embeddings va dung so chieu (research R2)."""
        vector = self.embed(["probe"])[0]
        if len(vector) != self._dimensions:
            raise ConfigError(f"model tra {len(vector)} chieu, can {self._dimensions} (bang knowledge_chunks)")
