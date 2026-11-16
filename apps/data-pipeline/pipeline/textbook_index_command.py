"""index-textbook (spec 012, contracts/pipeline-cli-textbook.md): doan da xu ly + decisions da duyet -> knowledge_chunks.

Thu tu: manifest -> file da xu ly -> decisions -> check_ready (tat ca offline, loi -> ma 1) -> moi toi cau hinh embedding
va DB (loi -> ma 2). Phan can DB nam o index_textbook_records de test duoc voi embedder gia. Ma thoat: 0 xong;
1 loi dau vao / kho con ban ghi textbook sot; 2 preflight; 3 ghi xong nhung con embedding loi.
"""
import argparse
import sys
from typing import Callable, Collection, Dict, List, Sequence

import psycopg

from .embedding_client import EmbeddingClient
from .knowledge_chunk_writer import PreflightError, existing_hashes, plan_writes, preflight, write_records
from .settings import TEXTBOOK_SOURCE_TYPE, ConfigError, require_index_settings
from .textbook_command_common import load_checked_manifest, select_sources
from .textbook_manifest_models import dataset_name
from .textbook_processed_io import processed_path, read_jsonl
from .textbook_review_decisions import Decisions, load_decisions

EXIT_OK, EXIT_INPUT_ERROR, EXIT_PREFLIGHT, EXIT_EMBED_ERRORS = 0, 1, 2, 3
EmbedFn = Callable[[Sequence[str]], List[List[float]]]


def check_ready(records: Sequence[Dict], decisions: Decisions) -> List[str]:
    """Ly do chua ghi duoc (rong = san sang): decisions chua duyet, hoac con doan chua soat (khong co metadata.review)."""
    problems: List[str] = []
    if not decisions.approved_by.strip():
        problems.append(f"decisions cua {decisions.source_id} chua duoc duyet (approved_by rong)")
    unreviewed = [r for r in records if not r["metadata"].get("review")]
    if unreviewed:
        problems.append(f"{len(unreviewed)} doan chua co quyet dinh soat (vd hash {unreviewed[0]['content_hash']}): "
                        "chay review-textbook-prepare / review-textbook-score roi process-textbook")
    return problems


def _counts_by_source_type(conn) -> Dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT source_type, count(*) FROM knowledge_chunks GROUP BY source_type")
        return {row[0]: row[1] for row in cur.fetchall()}


def _stray_textbook_datasets(conn, known_datasets: Collection[str]) -> List[str]:
    """Dataset co ban ghi source_type textbook trong kho nhung khong thuoc nguon nao trong manifest (ban ghi sot)."""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT metadata->>'dataset' FROM knowledge_chunks WHERE source_type = %s",
                    (TEXTBOOK_SOURCE_TYPE,))
        found = [row[0] for row in cur.fetchall()]
    return sorted(str(name) for name in found if name not in known_datasets)


def _print_counts(label: str, counts: Dict[str, int]) -> None:
    body = ", ".join(f"{name}={counts[name]}" for name in sorted(counts)) or "(rong)"
    print(f"   kho {label}: {body}")


def index_textbook_records(conn, records: Sequence[Dict], embed: EmbedFn, probe: Callable[[], None],
                           stored_model: str, known_datasets: Collection[str]) -> int:
    """Phan can DB cua index-textbook: preflight -> dem truoc -> kiem ban ghi sot -> plan -> probe (chi khi co ban ghi
    moi, chay lai khong goi API) -> ghi -> dem sau. PreflightError / loi DB noi len cho run_index_textbook."""
    preflight(conn)
    before = _counts_by_source_type(conn)
    _print_counts("truoc", before)
    stray = _stray_textbook_datasets(conn, known_datasets)
    if stray:
        print(f"loi: kho co ban ghi textbook khong thuoc nguon nao trong manifest: {', '.join(stray)}. "
              "Xoa chung (hoac them manifest) roi chay lai; chua ghi gi.", file=sys.stderr)
        return EXIT_INPUT_ERROR
    plan = plan_writes(records, existing_hashes(conn, [r["content_hash"] for r in records]))
    if plan.new:
        probe()
    stats = write_records(conn, plan, embed, stored_model)
    stats["skipped_same"] = len(plan.update)
    _print_counts("sau", _counts_by_source_type(conn))
    print("   " + ", ".join(f"{key}={value}" for key, value in stats.items()))
    return EXIT_EMBED_ERRORS if stats["embed_errors"] else EXIT_OK


def run_index_textbook(args: argparse.Namespace) -> int:
    check = load_checked_manifest()
    if check is None:
        return EXIT_INPUT_ERROR
    source_ids = getattr(args, "source", None) or []
    if not source_ids:
        print("loi: index-textbook can --source", file=sys.stderr)
        return EXIT_INPUT_ERROR
    sources = select_sources(check, source_ids)
    if sources is None:
        return EXIT_INPUT_ERROR
    batches, failed = [], False
    for source in sources:
        path = processed_path(source.source_id)
        if not path.is_file():
            print(f"loi: [{source.source_id}] chua co {path}: chay process-textbook", file=sys.stderr)
            failed = True
            continue
        try:
            records, decisions = read_jsonl(path), load_decisions(source.source_id)
        except ValueError as exc:
            print(f"loi: [{source.source_id}] {exc}", file=sys.stderr)
            failed = True
            continue
        for problem in check_ready(records, decisions):
            print(f"loi: [{source.source_id}] {problem}", file=sys.stderr)
            failed = True
        batches.append((source, records))
    if failed:
        return EXIT_INPUT_ERROR
    known = {dataset_name(s.source_id) for s in check.sources}  # moi nguon trong manifest, ke ca excluded
    try:
        settings = require_index_settings()
        client = EmbeddingClient(settings)
        with psycopg.connect(settings.db_url) as conn:
            codes = []
            for source, records in batches:
                print(f"== {source.source_id}: {len(records)} ban ghi")
                codes.append(index_textbook_records(conn, records, client.embed, client.probe,
                                                    settings.stored_model, known))
            return max(codes)
    except (ConfigError, PreflightError, psycopg.OperationalError) as exc:
        print(f"loi preflight: {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT
