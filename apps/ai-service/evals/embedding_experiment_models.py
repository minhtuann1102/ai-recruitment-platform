"""Danh sach model, phien ban HF da ghim, va ham embed (sentence-transformers CPU / OpenAI) cho thi nghiem embedding.
torch + sentence-transformers chi import khi dung model ST (ham ben trong) de module nap duoc khi chua cai deps thi nghiem.
"""
import asyncio
import os
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

THREADS = 4  # VM staging e2-standard-4 = 4 vCPU, khong GPU
OPENAI_MAX_TOKENS = 8191  # gioi han dau vao cua text-embedding-3-*
OPENAI_PRICE_PER_M = {"oa-large": 0.13, "oa-small": 0.02}  # USD / 1M token (bang gia OpenAI chuan)


@dataclass(frozen=True)
class ModelSpec:
    id: str
    kind: str  # openai | st
    name: str  # ten API hoac repo HF
    dims: int
    query_prefix: str = ""
    doc_prefix: str = ""


SPECS: Dict[str, ModelSpec] = {s.id: s for s in (
    ModelSpec("oa-small", "openai", "text-embedding-3-small", 1536),
    ModelSpec("oa-large", "openai", "text-embedding-3-large", 1536),
    ModelSpec("st-minilm", "st", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 384),
    ModelSpec("st-e5", "st", "intfloat/multilingual-e5-base", 768, "query: ", "passage: "),
    ModelSpec("st-bge", "st", "BAAI/bge-m3", 1024),
)}
# Commit HF da ghim (model_info(repo).sha luc chay 26/11/2026); thieu thi tra cuu ban moi nhat va canh bao
REVISIONS: Dict[str, str] = {
    "st-minilm": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
    "st-e5": "d128750597153bb5987e10b1c3493a34e5a4502a",
    "st-bge": "5617a9f61b028005a4858fdac845db406aefb181",
}


def resolve_revision(spec: ModelSpec) -> str:
    if spec.kind == "openai":
        return "api"
    if spec.id in REVISIONS:
        return REVISIONS[spec.id]
    from huggingface_hub import HfApi
    sha = HfApi().model_info(spec.name).sha
    print(f"CANH BAO: {spec.id} chua ghim revision, dung {sha} (them vao REVISIONS)", flush=True)
    return sha


def peak_rss_mb() -> float:
    """RSS dinh cua tien trinh (MB): peak_wset tren Windows, ru_maxrss tren Linux/macOS."""
    import psutil
    info = psutil.Process().memory_info()
    peak = getattr(info, "peak_wset", None)
    if peak is None:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return peak / 1e6


def load_st(spec: ModelSpec, revision: str):
    """(model, giay nap, cache_lanh). cache_lanh=True: lan dau, thoi gian nap gom ca tai ve nen khong dung de bao cao."""
    import torch
    from huggingface_hub import try_to_load_from_cache
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(THREADS)
    # lanh = chua co file trong so trong cache (config.json mot minh khong du: tai ve do dang co the da co san)
    cold = not any(isinstance(try_to_load_from_cache(spec.name, f, revision=revision), str)
                   for f in ("model.safetensors", "pytorch_model.bin"))
    t0 = time.perf_counter()
    model = SentenceTransformer(spec.name, revision=revision, device="cpu")
    return model, time.perf_counter() - t0, cold


def st_token_lengths(model, texts: Sequence[str]) -> List[int]:
    """So token moi van ban theo tokenizer cua chinh model (gom token dac biet, khong cat)."""
    out: List[int] = []
    for i in range(0, len(texts), 1000):
        ids = model.tokenizer(list(texts[i:i + 1000]), add_special_tokens=True, truncation=False,
                              return_attention_mask=False)["input_ids"]
        out.extend(len(x) for x in ids)
    return out


def st_encode(model, texts: Sequence[str], batch_size: int) -> np.ndarray:
    return model.encode(list(texts), batch_size=batch_size, convert_to_numpy=True, normalize_embeddings=False,
                        show_progress_bar=False)


def openai_token_lengths(texts: Sequence[str]) -> List[int]:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")  # bo ma hoa cua ho text-embedding-3
    return [len(x) for x in enc.encode_batch(list(texts), disallowed_special=())]


def openai_model_name(base_url: str, name: str) -> str:
    """OpenAI truc tiep nhan ten tran; OpenRouter can tien to 'openai/'."""
    return f"openai/{name}" if "openrouter" in base_url else name


async def openai_embed(client, name: str, texts: Sequence[str], dims: int, *, batch: int = 100, concurrency: int = 4,
                       on_progress: Optional[Callable[[int, int], None]] = None) -> Tuple[np.ndarray, int]:
    """(vector theo thu tu dau vao, tong token tinh tien tu response.usage)."""
    sem = asyncio.Semaphore(concurrency)
    out: List[Optional[List[float]]] = [None] * len(texts)
    tokens = 0

    async def one(start: int) -> None:
        nonlocal tokens
        async with sem:
            resp = await client.embeddings.create(model=name, input=list(texts[start:start + batch]), dimensions=dims)
            tokens += resp.usage.total_tokens
            for i, d in enumerate(resp.data):
                out[start + i] = d.embedding
            if on_progress:
                on_progress(min(start + batch, len(texts)), len(texts))

    await asyncio.gather(*(one(s) for s in range(0, len(texts), batch)))
    return np.array(out, dtype=np.float32), tokens


def disable_tracing() -> None:
    """Khong gui trace Langfuse khi chay eval (goi truoc khi import app.llm)."""
    os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "false")
