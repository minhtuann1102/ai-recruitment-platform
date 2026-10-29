"""Hybrid search (plans/261029-1415-hybrid-grounded-rag, Phase 01): chay song song tim theo tu khoa (BM25 trong bo
nho, app/rag/bm25_index.py) va vector, cong them danh sach truyen vao (vd theo topic_id), gop bang RRF co trong so
(hybrid_fusion.rrf: tu khoa 0.5, con lai 1.0).

- Tu khoa bat thuat ngu Anh / ten rieng khop chinh xac (diem yeu cua vector voi truy van tieng Viet).
- Vector bat cach dien dat khac nghia gan.
- topic_id chi la mot danh sach trong RRF (tang diem), khong loc cung: topic_id cua kho DE gan con rong.
Mot duong loi thi van dung cac duong con lai va ghi `rag_hybrid_partial` (khong ngat RAG); tat ca loi thi nem loi.
Van ban tim kiem (truy van + ban tieng Anh LLM viet lai, do 29/10 tot hon truy van goc cho ca BM25) va vector cache
theo truy van trong process: snippet va ngan hang cau hoi cua cung topic dung chung mot lan viet lai + embed. Viet
lai loi (tra ve tu dien) thi khong cache, lan sau thu lai.
Viet lai + embed co han RESOLVE_BUDGET_S: qua han thi BM25 dung truy van goc, duong vector tinh la loi (partial), van
tra topic + BM25 truoc han snippet thay vi mat het. Task viet lai/embed van chay tiep va vao cache cho lan sau.
"""
import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

from ..llm.usage import UsageCollector
from .bm25_index import Bm25Store
from .hybrid_fusion import LEXICAL_WEIGHT, rrf
from .models import Chunk, SearchFilters

log = logging.getLogger("ai_service.rag")
PARTIAL_ERROR = "rag_hybrid_partial"
CACHE_MAX = 256
# Do 29/10 (Supabase + OpenRouter): viet lai 1.2-2.5 s, embed 1.0-1.3 s, SQL vector + kho cau 0.5-1.1 s. Han snippet
# 5 s (plan_snippets.SNIPPET_DEADLINE_S) tru phan SQL con lai.
RESOLVE_BUDGET_S = 3.5


class HybridSearcher:
    def __init__(self, repo, embed: Callable[..., Awaitable[List[float]]],
                 search_text: Callable[..., Awaitable[Tuple[str, bool]]]):
        """search_text(query, collector) -> (van ban, co cache duoc khong): False khi LLM viet lai loi."""
        self._repo, self._embed, self._search_text = repo, embed, search_text
        self.bm25 = Bm25Store(repo.load_corpus, version=getattr(repo, "corpus_version", None))
        self._done: Dict[str, Tuple[str, List[float]]] = {}
        self._inflight: Dict[str, asyncio.Task] = {}

    async def _resolve(self, query: str, collector: Optional[UsageCollector]) -> Tuple[str, List[float]]:
        """(van ban tim kiem, vector). Da xong thi tra lai; dang tinh thi cho chung. shield: request A het han
        (wait_for huy A) khong huy task dung chung ma request B dang cho. Loi hay viet lai loi thi khong luu."""
        if query in self._done:
            return self._done[query]
        task = self._inflight.get(query)
        if task is None:
            task = self._inflight[query] = asyncio.ensure_future(self._make(query, collector))
            task.add_done_callback(lambda t, q=query: self._store(q, t))
        text, vector, _ = await asyncio.shield(task)
        return text, vector

    async def _resolve_in_budget(self, query: str, collector: Optional[UsageCollector]) -> Tuple[str, List[float]]:
        """Nhu _resolve nhung nem asyncio.TimeoutError sau RESOLVE_BUDGET_S (task dung chung khong bi huy)."""
        return await asyncio.wait_for(self._resolve(query, collector), RESOLVE_BUDGET_S)

    async def query_vector(self, query: str, collector: Optional[UsageCollector] = None) -> List[float]:
        return (await self._resolve_in_budget(query, collector))[1]

    async def _make(self, query: str, collector: Optional[UsageCollector]) -> Tuple[str, List[float], bool]:
        text, keep = await self._search_text(query, collector)
        return text, await self._embed(text, collector=collector), keep

    def _store(self, query: str, task: asyncio.Task) -> None:
        self._inflight.pop(query, None)
        if task.cancelled() or task.exception() is not None:
            return
        text, vector, keep = task.result()
        if keep:
            if len(self._done) >= CACHE_MAX:
                self._done.clear()
            self._done[query] = (text, vector)

    async def _lexical(self, query: str, filters: SearchFilters, limit: int,
                       collector: Optional[UsageCollector]) -> List[Chunk]:
        """BM25 tren cung van ban voi vector; viet lai / embed loi hay qua han thi BM25 dung truy van goc. Corpus chua
        nap xong (request den truoc khi warm xong) thi cung chi cho toi RESOLVE_BUDGET_S, roi tinh la loi (partial)."""
        async def text() -> str:
            try:
                return (await self._resolve_in_budget(query, collector))[0]
            except Exception:
                return query

        words, index = await asyncio.gather(text(), asyncio.wait_for(self.bm25.index(), RESOLVE_BUDGET_S))
        return index.search(words, filters, limit)

    async def _vector(self, query: str, filters: SearchFilters, limit: int,
                      collector: Optional[UsageCollector]) -> List[Chunk]:
        return await self._repo.search(await self.query_vector(query, collector), filters, limit)

    async def search(self, query: str, filters: SearchFilters, limit: int,
                     collector: Optional[UsageCollector] = None,
                     extra: Sequence[Awaitable[List[Chunk]]] = ()) -> List[Chunk]:
        """Gop [extra..., tu khoa, vector] bang RRF, tra toi da `limit` chunk (diem = diem RRF)."""
        names = [f"extra{i}" for i in range(len(extra))] + ["lexical", "vector"]
        weights = [1.0] * len(extra) + [LEXICAL_WEIGHT, 1.0]
        results = await asyncio.gather(*extra, self._lexical(query, filters, limit, collector),
                                       self._vector(query, filters, limit, collector), return_exceptions=True)
        failed = [(n, r) for n, r in zip(names, results) if isinstance(r, BaseException)]
        if len(failed) == len(results):
            err = failed[0][1]
            if not isinstance(err, Exception):  # CancelledError cua mot duong: coi la loi RAG, khong lam hong phien
                raise RuntimeError("rag_hybrid_cancelled") from err
            raise err
        if failed:
            log.warning("rag_hybrid_partial failed=%s", ",".join(f"{n}:{type(r).__name__}" for n, r in failed))
            if collector is not None:
                collector.rag_error(PARTIAL_ERROR)
        ok = [(r, w) for r, w in zip(results, weights) if not isinstance(r, BaseException)]
        log.info("rag_hybrid lists=%s", " ".join(f"{n}:{len(r)}" for n, r in zip(names, results)
                                                  if not isinstance(r, BaseException)))
        return rrf([r for r, _ in ok], [w for _, w in ok])[:limit]
