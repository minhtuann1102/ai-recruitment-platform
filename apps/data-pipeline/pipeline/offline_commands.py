"""Lenh offline: validate (US1) va process (US2). Khong can DB, khong can key (FR-009)."""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from .qa_record_builder import build_records
from .qa_seed_loader import SeedError, load_seed_items
from .qa_seed_validator import ValidationResult, validate_seed
from .run_report import RunReport
from .settings import CRAWLED_DATASET, CURATED_DATASET, ENRICHED_DIR, PROCESSED_DIR, SEEDS_DIR, catalog_dir
from .topic_catalog_reader import CatalogError, load_topic_categories

EXIT_OK, EXIT_INPUT_ERROR = 0, 1
PROCESSED_FILE = "interview_qa.jsonl"
MAX_ERRORS_SHOWN, MAX_WARNINGS_SHOWN = 50, 5


def _load_inputs(args: argparse.Namespace, strict: bool, near_duplicates: bool) -> Tuple[Dict[str, str], ValidationResult]:
    dirs = [catalog_dir()] + [Path(d) for d in getattr(args, "extra_catalog", [])]
    topics = load_topic_categories(dirs)
    items = load_seed_items([(SEEDS_DIR, CURATED_DATASET), (ENRICHED_DIR, CRAWLED_DATASET)])
    return topics, validate_seed(items, topics, strict=strict, near_duplicates=near_duplicates)


def _print_validation(result: ValidationResult) -> None:
    """In loi theo tung luat (toi da 50 vi du); canh bao chi in so luong + 5 vi du moi luat."""
    groups: Dict[Tuple[str, str], List] = {}
    for issue in sorted(result.issues, key=lambda i: (i.level, i.rule, i.qa_id or "")):
        groups.setdefault((issue.level, issue.rule), []).append(issue)
    for (level, rule), issues in groups.items():
        limit = MAX_ERRORS_SHOWN if level == "error" else MAX_WARNINGS_SHOWN
        print(f"[{level}] {rule}: {len(issues)}")
        for issue in issues[:limit]:
            print(f"    {issue.qa_id or '-'}: {issue.message}")
    report = result.report
    print("== phan bo")
    print(f"cap: {report['pairs_valid']}/{report['pairs_in']} hop le; tu nguon ngoai {report['public_pairs']} ({report['public_share']:.0%})")
    print(f"dataset: {json.dumps(report['by_dataset'], ensure_ascii=False)}")
    print(f"topic du >= 2 cap: {report['topics_covered']}/{report['topics_in_catalog']}")
    for key in ("by_category", "by_difficulty", "by_language", "by_license", "by_source"):
        print(f"{key[3:]}: {json.dumps(report[key], ensure_ascii=False)}")
    topic_counts = ", ".join(f"{topic}={count}" for topic, count in report["by_topic"].items())
    print(f"topic: {topic_counts or '-'}")


def run_validate(args: argparse.Namespace) -> int:
    try:
        _, result = _load_inputs(args, strict=args.strict, near_duplicates=True)
    except (CatalogError, SeedError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    _print_validation(result)
    errors = len(result.errors)
    print(f"== {errors} loi, {len(result.issues) - errors} canh bao")
    return EXIT_INPUT_ERROR if errors else EXIT_OK


def rejected_entries(result: ValidationResult) -> List[Dict]:
    reasons: Dict[str, List[str]] = {}
    for issue in result.errors:
        if issue.qa_id is not None:
            reasons.setdefault(issue.qa_id, []).append(f"{issue.rule}: {issue.message}")
    return [{"qa_id": qa_id, "reasons": reasons[qa_id]} for qa_id in sorted(reasons)]


def process_seed(args: argparse.Namespace) -> Tuple[List[Dict], RunReport]:
    """Doc seed -> loai cap loi kem ly do -> ban ghi da dedup. Dung chung cho process va index."""
    topics, result = _load_inputs(args, strict=False, near_duplicates=False)
    records, dropped = build_records(result.valid, topics)
    report = RunReport(
        command=args.command,
        records_in=result.report["pairs_in"],
        records_rejected=rejected_entries(result),
        chunks_out=len(records),
        duplicates_dropped=dropped,
    )
    return records, report


def write_processed(records: List[Dict], out_dir: Path = PROCESSED_DIR) -> Path:
    """JSONL deterministic: sap san, sort_keys, khong timestamp (FR-009)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / PROCESSED_FILE
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def run_process(args: argparse.Namespace) -> int:
    try:
        records, report = process_seed(args)
    except (CatalogError, SeedError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    output = write_processed(records)
    report.print()
    print(f"ghi {output} va {report.write()}")
    return EXIT_OK
