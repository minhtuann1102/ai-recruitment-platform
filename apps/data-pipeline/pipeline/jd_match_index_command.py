"""index-jd-match (spec 017 US1, contracts/pipeline-cli-match.md): JD chuan hoa (process-jd) -> knowledge_chunks.

Moi JD co track (group) mot dong: source_type 'job_description', metadata.dataset 'jd-match'. Thu tu: nap file ->
dung ban ghi + kiem trung hash (offline, loi -> ma 1) -> cau hinh + DB (loi -> ma 2) -> kiem embedding_model cua dataset
(lech va khong co --rebuild -> ma 1, chua embed) -> [--rebuild: probe roi xoa dataset] -> plan_writes + write_records
-> run report. Khong co mock: vector gia khong bao gio ghi vao ai_db (research R8).
Ma thoat: 0 xong; 1 loi dau vao / lech model; 2 preflight hoac cau hinh; 3 ghi xong nhung con embedding loi.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import psycopg
from openai import OpenAIError

from .embedding_client import EmbeddingClient
from .jd_match_text import JD_MATCH_DATASET, JD_SOURCE_TYPE, build_match_records
from .knowledge_chunk_writer import PreflightError, existing_hashes, plan_writes, preflight, write_records
from .run_report import RunReport
from .settings import JD_NORMALIZED_PATH, PROCESSED_DIR, ConfigError, require_index_settings

EXIT_OK, EXIT_INPUT_ERROR, EXIT_PREFLIGHT, EXIT_EMBED_ERRORS = 0, 1, 2, 3
_MODELS_SQL = "SELECT DISTINCT embedding_model FROM knowledge_chunks WHERE source_type = %s AND metadata->>'dataset' = %s"
# Chi dong cua dataset jd-match va source_type job_description: dataset / source_type khac khong bi dong toi
_DELETE_DATASET_SQL = "DELETE FROM knowledge_chunks WHERE source_type = %s AND metadata->>'dataset' = %s"


class InputError(RuntimeError):
    pass


def load_jd_normalized(path: Path, limit: Optional[int] = None) -> List[Dict]:
    """N dong dau cua jd_normalized.jsonl (limit None = het). Dong hong / khong co jd_id -> InputError."""
    if not path.is_file():
        raise InputError(f"chua co {path}: chay process-jd")
    jds: List[Dict] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        if limit is not None and len(jds) >= limit:
            break
        try:
            jd = json.loads(line)
        except ValueError as exc:
            raise InputError(f"{path}:{number}: JSON loi ({exc})") from exc
        if not isinstance(jd, dict) or not jd.get("jd_id"):
            raise InputError(f"{path}:{number}: moi dong phai la object co jd_id")
        jds.append(jd)
    return jds


def _stored_models(conn) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(_MODELS_SQL, (JD_SOURCE_TYPE, JD_MATCH_DATASET))
        return sorted(row[0] for row in cur.fetchall())


def _delete_dataset(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(_DELETE_DATASET_SQL, (JD_SOURCE_TYPE, JD_MATCH_DATASET))
        deleted = cur.rowcount
    conn.commit()
    return deleted


def index_jd_match_records(conn, records: Sequence[Dict], embedder: EmbeddingClient, stored_model: str, *,
                           rebuild: bool = False, partial: bool = False) -> Tuple[int, Dict]:
    """Phan can DB, tach khoi viec tao ket noi / client de test duoc voi DB gia + embedder gia.

    embedder: embed / probe / total_tokens. partial (--limit): chi mot phan JD nen khong don ban ghi ngoai lan chay.
    Tra (ma thoat, bo dem); bo dem rong khi dung som (lech model, chua ghi gi).
    """
    preflight(conn)
    stale = [model for model in _stored_models(conn) if model != stored_model]
    if stale and not rebuild:
        print(f"loi: dataset {JD_MATCH_DATASET} da index bang model {', '.join(stale)}, cau hinh hien tai la "
              f"{stored_model}. Chay lai voi --rebuild (xoa dataset roi index lai); chua embed hay ghi gi.",
              file=sys.stderr)
        return EXIT_INPUT_ERROR, {}
    deleted = 0
    if rebuild:
        embedder.probe()  # key hoac so chieu sai thi dung truoc khi xoa, khong de mat dataset
        deleted = _delete_dataset(conn)  # phai xoa truoc plan_writes: neu khong hash cu bi tinh la update, khong embed lai
    plan = plan_writes(records, existing_hashes(conn, [r["content_hash"] for r in records]))
    if partial:
        plan.keep_hashes = {}  # writer don moi ban ghi cung dataset khong co trong lan chay: --limit thi bo qua buoc don
    if plan.new and not rebuild:
        embedder.probe()  # chay lai khong co ban ghi moi thi khong goi API
    stats = write_records(conn, plan, embedder.embed, stored_model)
    stats["deleted"] += deleted
    if partial:
        stats["cleanup"] = "skipped (--limit)"
    stats["embedding_tokens"] = embedder.total_tokens
    return (EXIT_EMBED_ERRORS if stats["embed_errors"] else EXIT_OK), stats


def run_index_jd_match(args: argparse.Namespace) -> int:
    limit, rebuild = args.limit, bool(args.rebuild)
    if limit is not None and limit < 1:
        print("loi: --limit phai >= 1", file=sys.stderr)
        return EXIT_INPUT_ERROR
    if rebuild and limit is not None:  # xoa ca dataset roi chi ghi N JD: gan nhu chac chan la nham
        print("loi: --rebuild khong di cung --limit (se xoa ca dataset roi chi ghi mot phan)", file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        jds = load_jd_normalized(JD_NORMALIZED_PATH, limit)
    except InputError as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    records, skipped = build_match_records(jds)
    if not records:
        print(f"loi: khong co JD nao index duoc trong {JD_NORMALIZED_PATH} ({len(jds)} dong, {len(skipped)} bi bo)",
              file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        settings = require_index_settings()
        embedder = EmbeddingClient(settings)
        with psycopg.connect(settings.db_url) as conn:
            code, stats = index_jd_match_records(conn, records, embedder, settings.stored_model,
                                                 rebuild=rebuild, partial=limit is not None)
    except (ConfigError, PreflightError, psycopg.OperationalError, OpenAIError) as exc:
        print(f"loi preflight: {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT
    if not stats:  # dung som, chua ghi gi: khong co run report
        return code
    no_group, duplicates = (sum(1 for s in skipped if s["reason"] == r) for r in ("no_group", "duplicate_hash"))
    report = RunReport(
        command="index-jd-match", records_in=len(jds), chunks_out=len(records), duplicates_dropped=duplicates,
        records_rejected=[{"qa_id": s["jd_id"], "reasons": [s["reason"]]} for s in skipped],
    )
    report.index = {"input": len(jds), "skipped_no_group": no_group, "skipped_duplicate_hash": duplicates, **stats}
    report.print()
    print(f"ghi {report.write(PROCESSED_DIR)}")
    return code
