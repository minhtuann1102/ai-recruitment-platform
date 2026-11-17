"""Kiem tra truy hoi bang vector cho `coverage-textbook --db` (spec 012 T032, research R10).

Moi tinh huong: embed `query_en`, tim 3 doan gan nhat trong `knowledge_chunks` voi source_type = 'textbook' va category
thuoc hai category cua track; trung khi mot doan mang ma tinh huong trong metadata.scenario_ids. Chi doc, khong ghi kho.
SQL rieng vi knowledge_chunk_search.build_search_sql co dinh source_type cua interview_qa va loc category bang dau '='.
"""
import json
from typing import Dict, List, Sequence

import psycopg

from . import settings
from .embedding_client import EmbeddingClient
from .knowledge_chunk_writer import preflight, vector_literal
from .textbook_coverage_report import TOP_K, ScenarioQuery

SQL = (
    "SELECT metadata->'scenario_ids' FROM knowledge_chunks "
    "WHERE source_type = %s AND embedding_model = %s AND category = ANY(%s) "
    "ORDER BY embedding <=> %s::vector LIMIT %s"
)


def _ids(value) -> List[str]:
    """jsonb tra ve list; phong khi driver tra chuoi JSON."""
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, list) else []


def vector_hits(conn, items: Sequence[ScenarioQuery], vectors: Sequence[Sequence[float]], stored_model: str) -> Dict[str, bool]:
    """{ma tinh huong: co doan mang ma do trong TOP_K ket qua dau}; items va vectors cung thu tu."""
    hits: Dict[str, bool] = {}
    with conn.cursor() as cur:
        for (scn, _query, categories), vector in zip(items, vectors):
            cur.execute(SQL, [settings.TEXTBOOK_SOURCE_TYPE, stored_model, categories, vector_literal(vector), TOP_K])
            hits[scn] = any(scn in _ids(row[0]) for row in cur.fetchall())
    return hits


def run_vector_check(items: Sequence[ScenarioQuery]) -> Dict[str, bool]:
    """Mo client + ket noi that. Nem ConfigError / PreflightError / psycopg.OperationalError cho nguoi goi (ma thoat 2)."""
    cfg = settings.require_index_settings()
    vectors = EmbeddingClient(cfg).embed([query for _, query, _ in items]) if items else []
    with psycopg.connect(cfg.db_url) as conn:
        preflight(conn)
        return vector_hits(conn, items, vectors, cfg.stored_model)
