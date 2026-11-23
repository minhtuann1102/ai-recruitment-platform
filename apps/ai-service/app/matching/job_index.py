"""Snapshot chi muc JD trong bo nho cho goi y viec lam (spec 017 R5, data-model muc 2).

Nap tu ai_db.knowledge_chunks (source_type = 'job_description', metadata.dataset = 'jd-match') qua MOT ket noi psycopg
async ngan, dong ngay sau khi doc; khong dung chung pool RAG (pool chi ton tai khi RAG_ENABLED va khong dong vao
PgKnowledgeRepository cua AIE). Chi doc va statement_timeout tren Supabase do VAI TRO `aie_reader` ep (ALTER ROLE ...
default_transaction_read_only, statement_timeout); Supavisor bo tham so `options` luc ket noi nen READ_ONLY o day chi la
lop du phong. Tinh cosine tren ma tran numpy trong bo nho nen khong phu thuoc mang.
Vong doi: chua co -> mot task nap dung chung, moi request cho toi da connect_timeout + 5 s (qua han -> 503
match_index_unavailable, task van chay tiep o nen; bao shield nhu turn_reference_snippets: huy thang psycopg co the
treo); het han MATCH_INDEX_REFRESH_S -> request van dung ban cu, mot task nen nap lai (khong nap chong); nap nen loi
hoac ra rong (khi ban cu co JD) thi giu ban cu. Che do mock: chi muc mau mock_jobs.json + hash_embedder, khong cham ai_db.
"""
import asyncio
import logging
import math
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import psycopg

from ..api_error import ApiError
from ..llm.errors import ConfigError
from ..rag.repository import KEEPALIVES, READ_ONLY
from .job_snapshot import JobIndexSnapshot, build_mock_snapshot, rows_to_snapshot
from .settings import MatchSettings

log = logging.getLogger("ai_service.matching")

FAILURE_BACKOFF_S = 5.0  # nap lan dau loi: trong N giay request khac khong thu lai (khong ai cung cho het connect_timeout)
FIRST_LOAD_EXTRA_WAIT_S = 5.0  # request cho nap lan dau toi da connect_timeout_s + N giay

# Moi jd_id mot dong (PR-1); neu ban cu va moi cung ton tai thi dong moi nhat dung truoc va thang (rows_to_snapshot)
JD_SQL = ("SELECT embedding::text, metadata FROM knowledge_chunks "
          "WHERE source_type = 'job_description' AND metadata->>'dataset' = 'jd-match' AND embedding_model = %s "
          "ORDER BY metadata->>'jd_id', created_at DESC")


def _unavailable() -> ApiError:
    # khong dua DSN hay chi tiet driver vao thong bao (chi ten loi di vao log)
    return ApiError(503, "match_index_unavailable", "Chỉ mục JD chưa sẵn sàng (không đọc được ai_db), thử lại sau")


class JobIndex:
    def __init__(self, settings: MatchSettings, *, connect: Optional[Callable] = None,
                 monotonic: Callable[[], float] = time.monotonic, now: Optional[Callable[[], datetime]] = None,
                 wait_budget_s: Optional[float] = None):
        self._settings = settings
        self._connect = connect or psycopg.AsyncConnection.connect
        self._monotonic = monotonic
        self._now = now or (lambda: datetime.now(timezone.utc).replace(microsecond=0))
        self._wait_budget_s = (settings.connect_timeout_s + FIRST_LOAD_EXTRA_WAIT_S
                               if wait_budget_s is None else wait_budget_s)
        self._snapshot: Optional[JobIndexSnapshot] = None
        self._attempted_at = -math.inf  # lan nap (hoac len lich nap) gan nhat, thanh cong hay khong
        self._failed_at: Optional[float] = None
        self._first: Optional[asyncio.Future] = None  # task nap lan dau, dung chung giua cac request
        self._task: Optional[asyncio.Task] = None  # task lam moi nen

    @property
    def refresh_task(self) -> Optional[asyncio.Task]:
        return self._task

    async def get(self) -> JobIndexSnapshot:
        snapshot = self._snapshot
        if snapshot is None:
            return await self._first_load()
        stale = self._monotonic() - self._attempted_at > self._settings.index_refresh_s
        if stale and not self._settings.mock and (self._task is None or self._task.done()):
            self._attempted_at = self._monotonic()  # nap nen loi cung phai cho du MATCH_INDEX_REFRESH_S moi thu lai
            self._task = asyncio.ensure_future(self._refresh())
        return snapshot

    async def _first_load(self) -> JobIndexSnapshot:
        if self._first is None or self._first.done():
            if self._failed_at is not None and self._monotonic() - self._failed_at < FAILURE_BACKOFF_S:
                raise _unavailable()
            self._first = asyncio.ensure_future(self._load_first())
        try:  # shield: request het kien nhan khong huy lan nap (cac request khac van cho duoc ket qua)
            snapshot = await asyncio.wait_for(asyncio.shield(self._first), self._wait_budget_s)
        except asyncio.TimeoutError:
            log.warning("match_index_first_load_wait_timeout budget_s=%s", self._wait_budget_s)
            raise _unavailable() from None
        if snapshot is None:
            raise _unavailable()
        return snapshot

    async def _load_first(self) -> Optional[JobIndexSnapshot]:
        """Chay trong task rieng: loi ghi log + moc thoi gian roi tra None (khong nem, tranh 'exception never retrieved'
        khi moi request cho da het kien nhan)."""
        try:
            snapshot = await self._load()
        except Exception as err:
            self._failed_at = self._monotonic()
            log.warning("match_index_load_failed error=%s", type(err).__name__)
            return None
        self._snapshot, self._attempted_at = snapshot, self._monotonic()
        return snapshot

    async def _refresh(self) -> None:
        try:
            fresh = await self._load()
        except Exception as err:  # giu ban cu
            log.warning("match_index_refresh_failed error=%s", type(err).__name__)
            return
        current = self._snapshot
        if not len(fresh) and current is not None and len(current):
            # doi embedding_model hoac doc giua luc dang index: ban rong khong duoc thay ban co JD
            log.warning("match_index_refresh_empty kept=%d", len(current))
            return
        self._snapshot = fresh

    async def _load(self) -> JobIndexSnapshot:
        s = self._settings
        if s.mock:
            return build_mock_snapshot(self._now())
        if not s.db_url:
            raise ConfigError("AI_DB_URL chua dat")
        conn = await self._connect(s.db_url, autocommit=True, connect_timeout=s.connect_timeout_s, options=READ_ONLY,
                                   **KEEPALIVES)
        async with conn:  # dong ngay: khong giu slot cua pooler
            cursor = await conn.execute(JD_SQL, [s.embedding_model])
            rows = await cursor.fetchall()
        # parse ~360 x 1536 so mat ~0.2 s: ra thread de khong chan event loop cua request dang chay
        return await asyncio.to_thread(rows_to_snapshot, rows, s.embedding_model, self._now())
