"""Model embedding so sanh trong experiment 017 (plans/261126-2235-embedding-model-comparison, Phase 2).

Registry 5 model, cache vector theo (model, revision, sha256 cua van ban cuoi gom tien to) va ham goi OpenAI. Cache nam trong
data/processed/match_eval/embedding_cache (gitignore: chua CV tong hop + noi dung JD crawl). Import nang (openai, huggingface)
nam trong ham de test chi can numpy.
"""
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .settings import PROCESSED_DIR

CACHE_DIR = PROCESSED_DIR / "match_eval" / "embedding_cache"
QUERY, PASSAGE = "query", "passage"  # CV = query, JD = passage (e5 can tien to khac nhau)


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    kind: str  # "openai" | "st"
    name: str  # ten model API hoac HF repo
    dims: int
    query_prefix: str = ""
    passage_prefix: str = ""
    api_dimensions: Optional[int] = None  # chi gui `dimensions` khi dat (oa-large -> 1536)

    def final_text(self, role: str, text: str) -> str:
        return (self.query_prefix if role == QUERY else self.passage_prefix) + text


MODELS: Dict[str, ModelSpec] = {m.model_id: m for m in (
    ModelSpec("oa-small", "openai", "text-embedding-3-small", 1536),
    ModelSpec("oa-large", "openai", "text-embedding-3-large", 1536, api_dimensions=1536),
    ModelSpec("st-minilm", "st", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 384),
    ModelSpec("st-e5", "st", "intfloat/multilingual-e5-base", 768, query_prefix="query: ", passage_prefix="passage: "),
    ModelSpec("st-bge", "st", "BAAI/bge-m3", 1024),
)}


def text_key(final_text: str) -> str:
    return hashlib.sha256(final_text.encode("utf-8")).hexdigest()


class VectorCache:
    """Mot file JSON moi (model, revision): {key: vector}. Khong dung pickle."""

    def __init__(self, model_id: str, revision: str, dims: int, cache_dir: Path = CACHE_DIR):
        self.path = cache_dir / f"{model_id}__{revision[:12]}.json"
        self._meta = {"model_id": model_id, "revision": revision, "dims": dims}
        self._vectors: Dict[str, List[float]] = {}
        if self.path.is_file():
            doc = json.loads(self.path.read_text(encoding="utf-8"))
            if doc.get("revision") == revision and doc.get("dims") == dims:
                self._vectors = doc["vectors"]

    def get(self, final_text: str) -> Optional[np.ndarray]:
        vector = self._vectors.get(text_key(final_text))
        return None if vector is None else np.asarray(vector, dtype=np.float64)

    def put(self, final_text: str, vector: Sequence[float]) -> None:
        self._vectors[text_key(final_text)] = [float(x) for x in vector]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({**self._meta, "vectors": self._vectors}), encoding="utf-8")

    def covers(self, final_texts: Sequence[str]) -> bool:
        return all(text_key(t) in self._vectors for t in final_texts)


def ops_path(model_id: str, revision: str, cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / f"ops-{model_id}__{revision[:12]}.json"


def embed_openai_missing(spec: ModelSpec, items: Sequence[Tuple[str, str]], cache: VectorCache, api_key: str) -> Dict:
    """Embed phan chua co trong cache. CV (query) tung van ban mot nhu endpoint (do tre 1 lan goi), JD (passage) mot batch.

    Tra {latency_ms_query: [...], prompt_tokens, calls}; do tre la thoi gian mang toi OpenAI, khong so duoc voi CPU local.
    """
    from openai import OpenAI  # import tre: test thuan khong can SDK

    client = OpenAI(api_key=api_key, max_retries=3, timeout=60)
    extra = {"dimensions": spec.api_dimensions} if spec.api_dimensions else {}
    stats: Dict = {"latency_ms_query": [], "prompt_tokens": 0, "calls": 0}

    def call(texts: List[str]):
        started = time.perf_counter()
        response = client.embeddings.create(model=spec.name, input=texts, **extra)
        stats["calls"] += 1
        stats["prompt_tokens"] += getattr(getattr(response, "usage", None), "prompt_tokens", 0) or 0
        vectors = [d.embedding for d in sorted(response.data, key=lambda d: d.index)]
        if any(len(v) != spec.dims for v in vectors):
            raise RuntimeError(f"{spec.model_id}: so chieu khac {spec.dims}")
        return vectors, (time.perf_counter() - started) * 1000

    passages = [spec.final_text(PASSAGE, t) for r, t in items if r == PASSAGE and cache.get(spec.final_text(PASSAGE, t)) is None]
    if passages:
        vectors, _ = call(passages)
        for text, vector in zip(passages, vectors):
            cache.put(text, vector)
    for role, text in items:
        final = spec.final_text(role, text)
        if role == QUERY and cache.get(final) is None:
            vectors, ms = call([final])
            cache.put(final, vectors[0])
            stats["latency_ms_query"].append(ms)
    cache.save()
    return stats


def resolve_hf_revision(repo: str) -> str:
    """sha commit hien tai cua repo HF; ghi vao ket qua va dung lam revision khi tai / cache."""
    from huggingface_hub import HfApi

    return HfApi().model_info(repo).sha
