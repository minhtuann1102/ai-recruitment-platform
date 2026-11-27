"""Hai cong kiem tra truoc khi tin so lieu (thi nghiem embedding), doc ai_db chi doc + goi OpenAI:
(a) embed lai ~20 chunk bang 3-small, cosine voi vector da luu ~ 1.0 -> vector luu la embed dung `content`, nen cac model ST
    thay cung van ban;
(b) duong tim trong bo nho (oa-small, raw) so voi PgKnowledgeRepository.search tren cung vector truy van: top-5 giong nhau
    bao nhieu. Lech nho = chi muc ANN (neu co) cua ai_db xap xi, con trong bo nho chinh xac; ghi pg_indexes de giai thich.
"""
import asyncio
import dataclasses
from typing import Dict

import numpy as np
import psycopg

from app.llm.gateway import get_gateway
from app.rag.models import SearchFilters
from app.rag.repository import PgKnowledgeRepository
from app.rag.retriever import OVERFETCH, dedup
from app.rag.settings import load_rag_settings
from evals.embedding_experiment_cache import chunks_from_rows, load_corpus, read_json, text_key, write_json
from evals.embedding_experiment_core import normalize, retrieve_keys
from evals.embedding_experiment_embed import store_for
from evals.embedding_experiment_models import SPECS
from evals.embedding_experiment_queries import unique_queries

N_CONTENT_CHECK = 20


def _embedding_parity(rows, stored: np.ndarray) -> Dict:
    idx = np.linspace(0, len(rows) - 1, N_CONTENT_CHECK, dtype=int)
    fresh = asyncio.run(get_gateway().embed([rows[i]["content"] for i in idx]))
    cos = [float(normalize(np.array(f)) @ normalize(stored[i])) for f, i in zip(fresh, idx)]
    return {"n": len(cos), "cosine_min": round(min(cos), 5), "cosine_mean": round(float(np.mean(cos)), 5)}


async def _db_search_parity(queries, qvecs: Dict, matrix, chunks, k: int = 5) -> Dict:
    settings = dataclasses.replace(load_rag_settings(), connect_timeout_s=20)  # ket noi pooler moi mat ~3 s tu may nay
    repo = PgKnowledgeRepository(settings, connect=psycopg.AsyncConnection.connect)  # 1 ket noi moi lan
    same_list = same_set = 0
    overlap, diffs = [], []
    for q in queries:
        vec = normalize(np.array(qvecs[text_key(q)]))
        mine = retrieve_keys(matrix, chunks, vec, k)
        db = [c.dedup_key for c in dedup(await repo.search(vec.tolist(), SearchFilters(("interview_qa",)), k * OVERFETCH))][:k]
        same_list += mine == db
        same_set += set(mine) == set(db)
        overlap.append(len(set(mine) & set(db)) / k)
        if mine != db:
            diffs.append({"query": q, "memory": mine, "db": db})
    return {"n_queries": len(queries), "identical_top5_order": same_list, "identical_top5_set": same_set,
            "mean_overlap": round(float(np.mean(overlap)), 4), "mismatches": diffs[:10]}


def _index_defs() -> list:
    url = load_rag_settings().db_url
    with psycopg.connect(url, connect_timeout=15, autocommit=True, prepare_threshold=None,
                         options="-c default_transaction_read_only=on") as conn:
        return [{"name": n, "def": d} for n, d in conn.execute(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'knowledge_chunks' ORDER BY 1").fetchall()]


def run_parity(versions: Dict[str, Dict]) -> Dict:
    rows = load_corpus()
    hashes = [r["content_hash"] for r in rows]
    spec = SPECS["oa-small"]
    stored = store_for(spec).matrix(hashes)
    qvecs = read_json("qvec-oa-small-api.json")
    if qvecs is None:
        raise SystemExit("Chay `queries --model oa-small` truoc")
    out = {"stored_vs_reembedded_3small": _embedding_parity(rows, stored),
           "memory_vs_pgvector_search": asyncio.run(_db_search_parity(
               unique_queries(versions), qvecs, normalize(stored), chunks_from_rows(rows))),
           "indexes_on_knowledge_chunks": _index_defs()}
    write_json("parity.json", out)
    return out
