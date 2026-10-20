"""Lenh can DB + key embedding: index (US3) va search (US3). Ma thoat theo contracts/pipeline-cli.md."""
import argparse
import sys
from typing import Callable, List, Sequence

import psycopg

from .embedding_client import EmbeddingClient
from .knowledge_chunk_search import search
from .knowledge_chunk_writer import PreflightError, existing_hashes, plan_writes, preflight, write_records
from .offline_commands import process_seed
from .qa_seed_loader import SeedError
from .settings import ConfigError, require_index_settings
from .topic_catalog_reader import CatalogError

EXIT_OK, EXIT_INPUT, EXIT_PREFLIGHT, EXIT_EMBED_ERRORS = 0, 1, 2, 3
EmbedFn = Callable[[Sequence[str]], List[List[float]]]


def index_records(args: argparse.Namespace, conn, embed: EmbedFn, probe: Callable[[], None], stored_model: str) -> int:
    """Phan loi cua index, tach khoi viec tao ket noi / client de test duoc voi embedder gia."""
    try:
        records, report = process_seed(args)
    except (CatalogError, SeedError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT
    preflight(conn)
    plan = plan_writes(records, existing_hashes(conn, [r["content_hash"] for r in records]))
    if plan.new:
        probe()  # chi khi co ban ghi moi: chay lai khong goi API (SC-004)
    report.index = write_records(conn, plan, embed, stored_model)
    report.index["skipped_same"] = len(plan.update)
    report.print()
    print(f"ghi {report.write()}")
    return EXIT_EMBED_ERRORS if report.index["embed_errors"] else EXIT_OK


def run_index(args: argparse.Namespace) -> int:
    try:
        settings = require_index_settings()
        client = EmbeddingClient(settings)
        with psycopg.connect(settings.db_url) as conn:
            return index_records(args, conn, client.embed, client.probe, settings.stored_model)
    except (ConfigError, PreflightError, psycopg.OperationalError) as exc:
        print(f"loi preflight: {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT


def run_search(args: argparse.Namespace) -> int:
    try:
        settings = require_index_settings()
        client = EmbeddingClient(settings)
        filters = {"category": args.category, "difficulty": args.difficulty, "topic_id": args.topic_id, "chunk_type": args.chunk_type}
        with psycopg.connect(settings.db_url) as conn:
            preflight(conn)
            results = search(conn, client.embed([args.query])[0], filters, settings.stored_model, args.k)
    except (ConfigError, PreflightError, psycopg.OperationalError) as exc:
        print(f"loi preflight: {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT
    for rank, row in enumerate(results, 1):
        snippet = row["content"].replace("\n", " ")[:120]
        print(f"{rank}. {row['score']:.3f} {row['qa_id']} [{row['chunk_type']}] {row['topic_id']} | {snippet}")
    return EXIT_OK
