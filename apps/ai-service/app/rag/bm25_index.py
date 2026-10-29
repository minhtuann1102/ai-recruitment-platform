"""BM25 trong bo nho cho duong tu khoa cua hybrid search (thay Postgres full-text: ts_rank_cd khong co IDF nen tu
pho bien "du", "lieu", "khi" nang ngang tu hiem; chunk rat dai dung dau moi truy van; seq scan 1.7-4 s / truy van).
Do 29/10 (plans/reports/research-261029-1500-hybrid-vs-vector-rag.md): vector + BM25 RRF w=0.5 dat MRR held-out
0.852 -> 0.891, truy van < 17 ms.

Token: am tiet (giu dau tieng Viet, bo tu chuc nang) + cap am tiet lien nhau ("du_lieu", "bo_nho") de bat tu ghep.
Corpus: moi qa_pair cua interview_qa + textbook, nap mot lan (chi doc), build chay trong thread. Het TTL chi nap lai khi
dau van tay corpus doi: nap + build (~4 s) tranh GIL voi event loop, do 29/10 lam request dang chay qua han snippet.
"""
import asyncio
import logging
import math
import re
import time
import unicodedata
from collections import Counter, defaultdict
from typing import Awaitable, Callable, Dict, List, Optional, Sequence

from .models import Chunk, SearchFilters

log = logging.getLogger("ai_service.rag")
K1, B = 1.2, 0.75
CORPUS_TTL_S = 3600  # kho DE doi it (pipeline chay tay); lam moi moi gio
RETRY_AFTER_S = 60  # nap loi thi cho truoc khi thu lai, de request sau khong ton mot lan doc ca kho
LOAD_TIMEOUT_S = 30  # nap + dung binh thuong ~4-6 s; treo thi bo de task reset va thu lai (khong ket mai)

# Tu chuc nang pho bien (Viet + Anh), bo khoi token don (van nam trong cap am tiet)
STOPWORDS = frozenset("""
va la cua co khong cho nhu nao gi khi thi duoc trong voi mot cac nhung de bi tai sao vi neu ma hay hoac
và là của có không cho như nào gì khi thì được trong với một các những để bị tại sao vì nếu mà hãy hoặc
này đó thế làm ra vào lại đã đang sẽ rất cũng nhiều ít hơn bạn mình em anh chị ta họ giữa trên dưới sau trước
the a an of to in on for and or is are be was were it this that with as by at from how what why when which
do does can you your use using vs
""".split())


def tokens(text: str) -> List[str]:
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text.lower()))
    single = [w for w in words if len(w) >= 2 and w not in STOPWORDS]
    return single + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def _allowed(chunk: Chunk, filters: SearchFilters) -> bool:
    """Cung bo loc voi vector search (tru chunk_type: corpus chi co qa_pair, khu trung theo qa_id nhu nhau)."""
    if chunk.source_type not in filters.source_types:
        return False
    if filters.category and chunk.category != filters.category:
        return False
    return not filters.difficulty or chunk.difficulty in (filters.difficulty, None)


class Bm25Index:
    def __init__(self, chunks: Sequence[Chunk]):
        self.chunks = list(chunks)
        self._tf = [Counter(tokens(c.content)) for c in self.chunks]
        self._len = [sum(t.values()) for t in self._tf]
        self._avg = (sum(self._len) / len(self._len)) if self._len else 1.0
        df = Counter(w for t in self._tf for w in t)
        n = len(self.chunks)
        self._idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self._postings: Dict[str, List[int]] = defaultdict(list)
        for i, tf in enumerate(self._tf):
            for w in tf:
                self._postings[w].append(i)

    def search(self, query: str, filters: SearchFilters, limit: int) -> List[Chunk]:
        scores: Dict[int, float] = defaultdict(float)
        for w in set(tokens(query)):
            idf = self._idf.get(w)
            if not idf:
                continue
            for i in self._postings[w]:
                f = self._tf[i][w]
                scores[i] += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * self._len[i] / self._avg))
        ranked = sorted((i for i in scores if _allowed(self.chunks[i], filters)), key=lambda i: (-scores[i], i))
        return [self.chunks[i] for i in ranked[:limit]]


class Bm25Store:
    """Index dung chung trong process: nap lan dau (hoac warm luc khoi dong), het TTL thi nap lai, nap loi thi nem
    loi ngay trong RETRY_AFTER_S giay. Trong luc nap lai van dung index cu."""

    def __init__(self, load: Callable[[], Awaitable[List[Chunk]]], clock: Callable[[], float] = time.monotonic,
                 version: Optional[Callable[[], Awaitable[Optional[str]]]] = None):
        self._load, self._clock, self._version = load, clock, version
        self._index: Optional[Bm25Index] = None
        self._fingerprint: Optional[str] = None
        self._loaded_at = self._failed_at = -math.inf
        self._task: Optional[asyncio.Task] = None

    async def index(self) -> Bm25Index:
        now = self._clock()
        if self._index is not None and now - self._loaded_at < CORPUS_TTL_S:
            return self._index
        if self._index is None and now - self._failed_at < RETRY_AFTER_S:
            raise RuntimeError("bm25_corpus_unavailable")
        if self._task is None:
            self._task = asyncio.ensure_future(self._build())
        if self._index is not None:  # het TTL: nap lai o nen, van tra index cu
            return self._index
        await asyncio.shield(self._task)
        if self._index is None:
            raise RuntimeError("bm25_corpus_unavailable")
        return self._index

    async def _build(self) -> None:
        try:
            await asyncio.wait_for(self._load_and_build(), LOAD_TIMEOUT_S)
        except Exception as err:
            self._failed_at = self._clock()
            if self._index is not None:  # lam moi loi: dung index cu, thu lai sau RETRY_AFTER_S (khong moi request)
                self._loaded_at = self._failed_at - CORPUS_TTL_S + RETRY_AFTER_S
            log.warning("bm25_corpus_failed error=%s", type(err).__name__)
        finally:
            self._task = None

    async def _fingerprint_or_none(self) -> Optional[str]:
        """Dau van tay loi thi van nap (lan TTL sau nap lai chu khong so duoc), khong de no chan lan nap dau."""
        if self._version is None:
            return None
        try:
            return await self._version()
        except Exception as err:
            log.warning("bm25_corpus_version_failed error=%s", type(err).__name__)
            return None

    async def _load_and_build(self) -> None:
        version = await self._fingerprint_or_none()
        if self._index is not None and version is not None and version == self._fingerprint:
            self._loaded_at = self._clock()
            log.info("bm25_corpus_unchanged")
            return
        chunks = await self._load()
        started = time.perf_counter()
        self._index = await asyncio.to_thread(Bm25Index, chunks)
        self._loaded_at, self._fingerprint = self._clock(), version
        log.info("bm25_corpus_loaded chunks=%d build_ms=%d", len(chunks), (time.perf_counter() - started) * 1000)
