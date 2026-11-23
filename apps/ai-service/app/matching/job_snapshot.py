"""Snapshot chi muc JD trong bo nho (spec 017 data-model muc 2): kieu du lieu, parse dong ai_db, chi muc mau mock.

Khong cham DB o day (job_index.py lo viec nap). Dong ai_db la (embedding::text, metadata); dong hong bi bo va dem,
jd_id trung thi giu dong dau tien (SQL xep dong moi nhat truoc).
"""
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .hash_embedder import EMBEDDING_DIMS, hash_embed
from .levels_tracks import level_rank
from .scorer import IndexedJob

log = logging.getLogger("ai_service.matching")

MOCK_JOBS_PATH = Path(__file__).resolve().parent / "mock_jobs.json"
MOCK_EMBEDDING_MODEL = f"mock-hash-{EMBEDDING_DIMS}"
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
