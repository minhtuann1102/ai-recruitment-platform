"""Doc chi muc JD cua 017 tu ai_db (chi doc) cho experiment embedding: giong job_index.JD_SQL + content / hash / created_at.

Dung DSN trong apps/ai-service/.env (vai tro aie_reader); doc bang dotenv_values chu khong qua os.environ vi hai file .env
khac nhau o nhieu bien. Khong in DSN hay mat khau, chi in ten vai tro. Giao dich READ ONLY lam lop du phong (Supavisor bo
tham so `options`, nen vai tro moi la lop ep that su).
"""
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from .match_embedding_ai_service import AI_SERVICE_DIR

# WHERE / ORDER BY nhu app/matching/job_index.JD_SQL (moi jd_id: dong moi nhat dung truoc va thang trong rows_to_snapshot)
JD_ROWS_SQL = ("SELECT embedding::text, metadata, content, content_hash, created_at FROM knowledge_chunks "
               "WHERE source_type = 'job_description' AND metadata->>'dataset' = 'jd-match' AND embedding_model = %s "
               "ORDER BY metadata->>'jd_id', created_at DESC")


@dataclass
class IndexRows:
    rows: List[Dict[str, Any]]
    db_role: str
    max_created_at: datetime


def read_db_url(env_path: Path = AI_SERVICE_DIR / ".env") -> str:
    from dotenv import dotenv_values

    url = (dotenv_values(env_path).get("AI_DB_URL") or "").strip()
    if not url:
        raise RuntimeError(f"chua dat AI_DB_URL trong {env_path}")
    return url


def _query_once(db_url: str, embedding_model: str):
    import psycopg

    with psycopg.connect(db_url, connect_timeout=15) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute("SELECT current_user")
            role = cur.fetchone()[0]
            cur.execute(JD_ROWS_SQL, [embedding_model])
            return role, [{"embedding_text": r[0], "metadata": r[1], "content": r[2], "content_hash": r[3], "created_at": r[4]}
                          for r in cur.fetchall()]


def fetch_index_rows(db_url: str, embedding_model: str, attempts: int = 3) -> IndexRows:
    import psycopg

    for attempt in range(1, attempts + 1):  # pooler Supabase thinh thoang cat ket noi giua chung (SSL closed): thu lai
        try:
            role, rows = _query_once(db_url, embedding_model)
            break
        except psycopg.OperationalError:
            if attempt == attempts:
                raise
            time.sleep(2 * attempt)
    if not rows:
        raise RuntimeError(f"chi muc jd-match rong cho embedding_model={embedding_model}")
    return IndexRows(rows, role, max(r["created_at"] for r in rows))


def first_row_per_jd(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """jd_id -> dong dau tien (moi nhat), cung quy tac dedup cua rows_to_snapshot."""
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        out.setdefault(str((row["metadata"] or {}).get("jd_id")), row)
    return out


def parse_vector(text: str) -> np.ndarray:
    return np.array(str(text).strip().strip("[]").split(","), dtype=np.float64)
