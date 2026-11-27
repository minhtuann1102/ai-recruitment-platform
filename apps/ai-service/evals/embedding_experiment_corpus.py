"""Doc kho interview_qa tu ai_db (CHI DOC, aie_reader) va golden set cho thi nghiem embedding.

Pham vi kho = source_type 'interview_qa' + embedding_model 'text-embedding-3-small', CA hai chunk_type (qa_pair + question):
dung bo loc cua evals/retrieval_experiment (SearchFilters(("interview_qa",)), khong loc chunk_type). Truong `corpus`
cua golden ('de_interview_qa') la ten bo canonical cua DE ung voi source_type nay; textbook / job_description loai ra.
Mot ket noi dong bo, doc theo trang khoa id (it ket noi cho Supabase pooler).
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import psycopg

from app.rag.settings import load_rag_settings
from evals.embedding_experiment_cache import save_corpus

SET_FILES = {"main": "rag_golden.json", "holdout": "rag_golden_holdout.json"}
STORED_MODEL = "text-embedding-3-small"
READ_ONLY = "-c default_transaction_read_only=on -c statement_timeout=120000"
NIL_UUID = "00000000-0000-0000-0000-000000000000"
PAGE_SQL = ("SELECT id::text, content, content_hash, metadata->>'qa_id', metadata->>'chunk_type', topic_id, category, "
            "difficulty, embedding::text FROM knowledge_chunks WHERE source_type = 'interview_qa' "
            "AND embedding_model = %s AND id > %s::uuid ORDER BY id LIMIT %s")
COUNT_SQL = "SELECT count(*) FROM knowledge_chunks WHERE source_type = 'interview_qa' AND embedding_model = %s"


def parse_vector(text: str) -> np.ndarray:
    """pgvector text '[0.1,0.2,...]' -> float32."""
    return np.array(text.strip("[]").split(","), dtype=np.float32)


def _connect(url: str):
    return psycopg.connect(url, connect_timeout=15, autocommit=True, prepare_threshold=None, options=READ_ONLY)


def fetch_corpus(page: int = 500) -> Tuple[List[Dict], np.ndarray, int]:
    """(hang theo id, ma tran vector 3-small da luu, so dong dem tu DB). Mat ket noi giua chung thi noi lai tiep tuc."""
    url = load_rag_settings().db_url
    rows: List[Dict] = []
    vecs: List[np.ndarray] = []
    last, conn, retries = NIL_UUID, _connect(url), 0
    try:
        total = conn.execute(COUNT_SQL, [STORED_MODEL]).fetchone()[0]
        while True:
            try:
                batch = conn.execute(PAGE_SQL, [STORED_MODEL, last, page]).fetchall()
            except psycopg.OperationalError:
                retries += 1
                if retries > 3:
                    raise
                conn.close()
                conn = _connect(url)
                continue
            if not batch:
                break
            for r in batch:
                rows.append({"id": r[0], "content": r[1], "content_hash": r[2], "qa_id": r[3], "chunk_type": r[4],
                             "topic_id": r[5], "category": r[6], "difficulty": r[7]})
                vecs.append(parse_vector(r[8]))
            last = batch[-1][0]
            print(f"fetched {len(rows)}/{total}", flush=True)
    finally:
        conn.close()
    return rows, np.vstack(vecs), total


def persist_corpus(rows: Sequence[Dict]) -> str:
    """Ghi corpus.jsonl, tra dau van tay (md5 cac content_hash theo thu tu id)."""
    save_corpus(rows)
    return hashlib.md5("".join(r["content_hash"] for r in rows).encode()).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_golden_versions(dirs: Dict[str, Path]) -> Dict[str, Dict]:
    """{version: {'dir', 'sha256': {file: sha}, 'sets': {main|holdout: golden dict}}}; thu muc/ file khong doc duoc thi bo."""
    out: Dict[str, Dict] = {}
    for version, d in dirs.items():
        found = {name: d / fname for name, fname in SET_FILES.items() if (d / fname).exists()}
        if not found:
            continue
        out[version] = {"dir": str(d), "sha256": {p.name: sha256_file(p) for p in found.values()},
                        "sets": {n: json.loads(p.read_text(encoding="utf-8")) for n, p in found.items()}}
    return out


def precheck_missing(versions: Dict[str, Dict], corpus_qa_ids: Sequence[str]) -> Dict[str, Dict[str, Dict]]:
    """Dem id `relevant` cua golden khong con trong kho (tran recall). Tinh theo qa_id, khong theo id chunk."""
    have, out = set(corpus_qa_ids), {}
    for version, v in versions.items():
        for name, golden in v["sets"].items():
            queries = golden["queries"]
            relevant = {r for q in queries for r in q["relevant"]}
            missing = sorted(relevant - have)
            dead = [q["id"] for q in queries if not set(q["relevant"]) & have]  # truy van khong the trung
            partial = [q["id"] for q in queries if set(q["relevant"]) - have and set(q["relevant"]) & have]
            out.setdefault(version, {})[name] = {
                "n_queries": len(queries), "n_relevant_ids": len(relevant), "n_missing_ids": len(missing),
                "missing_ids": missing, "queries_all_relevant_missing": dead, "queries_some_relevant_missing": partial,
                "recall_ceiling": round(1 - len(dead) / len(queries), 4)}
    return out
