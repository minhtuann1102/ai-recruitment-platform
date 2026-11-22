"""Snapshot chi muc JD trong bo nho cho goi y viec lam (spec 017 R5, data-model muc 2).

Nap tu ai_db.knowledge_chunks (source_type = 'job_description', metadata.dataset = 'jd-match') qua MOT ket noi psycopg
async ngan, read-only, dong ngay sau khi doc; khong dung chung pool RAG (pool chi ton tai khi RAG_ENABLED va khong
dong vao PgKnowledgeRepository cua AIE). Tinh cosine tren ma tran numpy trong bo nho nen khong phu thuoc mang.
Vong doi: chua co -> request dau nap (loi -> 503 match_index_unavailable); het han MATCH_INDEX_REFRESH_S -> request
van dung ban cu, mot task nen nap lai (co khoa, khong nap chong); nap nen loi thi giu ban cu. Che do mock: chi muc mau
mock_jobs.json + hash_embedder, khong cham ai_db.
"""
import asyncio
import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import psycopg

from ..api_error import ApiError
from ..llm.errors import ConfigError
from ..rag.repository import KEEPALIVES, READ_ONLY
from .hash_embedder import EMBEDDING_DIMS, hash_embed
from .levels_tracks import level_rank
from .scorer import IndexedJob
from .settings import MatchSettings

log = logging.getLogger("ai_service.matching")

MOCK_JOBS_PATH = Path(__file__).resolve().parent / "mock_jobs.json"
MOCK_EMBEDDING_MODEL = f"mock-hash-{EMBEDDING_DIMS}"
FAILURE_BACKOFF_S = 5.0  # nap lan dau loi: trong N giay request khac khong thu lai (khong ai cung cho het connect_timeout)

# Moi jd_id mot dong (PR-1); neu ban cu va moi cung ton tai thi dong moi nhat dung truoc va thang (rows_to_snapshot)
JD_SQL = ("SELECT embedding::text, metadata FROM knowledge_chunks "
          "WHERE source_type = 'job_description' AND metadata->>'dataset' = 'jd-match' AND embedding_model = %s "
          "ORDER BY metadata->>'jd_id', created_at DESC")


@dataclass(frozen=True)
class JobIndexSnapshot:
    jobs: Tuple[IndexedJob, ...]
    matrix: np.ndarray  # N x EMBEDDING_DIMS, moi hang da chuan hoa L2; hang i ung voi jobs[i]
    embedding_model: str
    loaded_at: datetime  # UTC
    source: str  # "ai_db" | "mock"

    def __len__(self) -> int:
        return len(self.jobs)


def _parse_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def job_from_metadata(meta: Any) -> Optional[IndexedJob]:
    """metadata cua dong ai_db (data-model muc 1) -> IndexedJob; thieu jd_id hoac group thi None (bo qua dong)."""
    if not isinstance(meta, dict) or not meta.get("jd_id") or not meta.get("group"):
        return None
    level = meta.get("level") or None
    skills = meta.get("skills")
    return IndexedJob(
        job_id=str(meta["jd_id"]), title=str(meta.get("title") or ""), group=str(meta["group"]), level=level,
        level_rank=level_rank(level), deadline=_parse_date(meta.get("deadline")),
        skills=frozenset(s for s in skills if isinstance(s, str)) if isinstance(skills, list) else frozenset())


def _parse_vector(text: Any) -> Optional[np.ndarray]:
    """'[0.1,0.2,...]' (embedding::text) -> vector chuan hoa L2; sai dang, sai so chieu, vo han hay vector 0 -> None."""
    try:
        vector = np.array(str(text).strip().strip("[]").split(","), dtype=np.float64)
    except ValueError:
        return None
    if vector.shape != (EMBEDDING_DIMS,) or not np.isfinite(vector).all():
        return None
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else None


def _snapshot(items: Sequence[Tuple[IndexedJob, np.ndarray]], model: str, loaded_at: datetime,
              source: str) -> JobIndexSnapshot:
    matrix = np.vstack([v for _, v in items]) if items else np.zeros((0, EMBEDDING_DIMS))
    return JobIndexSnapshot(tuple(j for j, _ in items), matrix, model, loaded_at, source)


def rows_to_snapshot(rows: Sequence[Tuple[Any, Any]], model: str, loaded_at: datetime,
                     source: str = "ai_db") -> JobIndexSnapshot:
    """Dong (embedding::text, metadata) -> snapshot. Dong hong bi bo va dem; jd_id trung thi giu dong dau tien."""
    items: List[Tuple[IndexedJob, np.ndarray]] = []
    seen, skipped, duplicates = set(), 0, 0
    for embedding_text, meta in rows:
        job, vector = job_from_metadata(meta), _parse_vector(embedding_text)
        if job is None or vector is None:
            skipped += 1
        elif job.job_id in seen:
            duplicates += 1
        else:
            seen.add(job.job_id)
            items.append((job, vector))
    if skipped or duplicates:
        log.warning("match_index_rows_skipped count=%d duplicates=%d", skipped, duplicates)
    if not items:
        log.warning("match_index_empty model=%s hint=%s", model, "chua chay index-jd-match hoac embedding_model lech")
    return _snapshot(items, model, loaded_at, source)


def build_mock_snapshot(loaded_at: datetime) -> JobIndexSnapshot:
    """Chi muc mau tu mock_jobs.json, vector gia tu hash_embedder (khong bao gio ghi vao ai_db)."""
    rows: List[Dict[str, Any]] = json.loads(MOCK_JOBS_PATH.read_text(encoding="utf-8"))
    items = [(job_from_metadata(r["metadata"]), hash_embed(r["content"])) for r in rows]
    return _snapshot(items, MOCK_EMBEDDING_MODEL, loaded_at, "mock")


def _unavailable() -> ApiError:
    # khong dua DSN hay chi tiet driver vao thong bao (chi ten loi di vao log)
    return ApiError(503, "match_index_unavailable", "Chỉ mục JD chưa sẵn sàng (không đọc được ai_db), thử lại sau")


class JobIndex:
    def __init__(self, settings: MatchSettings, *, connect: Optional[Callable] = None,
                 monotonic: Callable[[], float] = time.monotonic, now: Optional[Callable[[], datetime]] = None):
        self._settings = settings
        self._connect = connect or psycopg.AsyncConnection.connect
        self._monotonic = monotonic
        self._now = now or (lambda: datetime.now(timezone.utc).replace(microsecond=0))
        self._snapshot: Optional[JobIndexSnapshot] = None
        self._lock = asyncio.Lock()  # mot lan nap tai mot thoi diem: nap dau va nap nen khong chong nhau
        self._attempted_at = -math.inf  # lan nap (hoac len lich nap) gan nhat, thanh cong hay khong
        self._failed_at: Optional[float] = None
        self._task: Optional[asyncio.Task] = None

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
        async with self._lock:
            if self._snapshot is not None:
                return self._snapshot
            if self._failed_at is not None and self._monotonic() - self._failed_at < FAILURE_BACKOFF_S:
                raise _unavailable()
            try:
                snapshot = await self._load()
            except Exception as err:
                self._failed_at = self._monotonic()
                log.warning("match_index_load_failed error=%s", type(err).__name__)
                raise _unavailable() from err
            self._snapshot, self._attempted_at = snapshot, self._monotonic()
            return snapshot

    async def _refresh(self) -> None:
        async with self._lock:
            try:
                self._snapshot = await self._load()
            except Exception as err:  # giu ban cu
                log.warning("match_index_refresh_failed error=%s", type(err).__name__)

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
