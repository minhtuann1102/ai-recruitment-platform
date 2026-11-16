"""process-textbook (spec 012, contracts/pipeline-cli-textbook.md): file tho moi nhat -> doan da xu ly, offline.

Doc `TEXTBOOK_RAW_DIR/<source_id>/<UTC>.jsonl` moi nhat + decisions (neu co), `build_records`, ghi
`TEXTBOOK_PROCESSED_DIR/<source_id>.jsonl` (cung input -> file giong het tung byte). Ma thoat: 0 xong;
1 manifest loi, nguon chua co file tho, hoac file tho / decisions / quyet dinh trim hong.
"""
import argparse
import sys

from .textbook_command_common import load_checked_manifest, select_sources
from .textbook_manifest_models import Source
from .textbook_processed_io import latest_raw_file, processed_path, read_jsonl, write_jsonl
from .textbook_record_builder import NOISE_REASONS, build_records
from .textbook_review_decisions import load_decisions

EXIT_OK, EXIT_INPUT_ERROR = 0, 1
DEDUP_WARN_RATIO = 0.05


def _print_stats(source: Source, raw_name: str, stats: dict) -> None:
    dropped = ", ".join(f"{key}={stats[key]}" for key in (*NOISE_REASONS, "review_drop", "too_short_after_trim"))
    print(f"== {source.source_id} ({raw_name}): {stats['pages_in']} trang vao, {stats['chunks']} doan tao, "
          f"{stats['records']} ban ghi")
    print(f"   bo: {dropped}")
    print(f"   trung: {stats['dedup']}; chua co quyet dinh soat: {stats['unreviewed']}")
    for miss in stats["section_misses"]:
        print(f"   [canh bao] dong manifest co `sections` nhung khong khop section nao cua trang: {miss}")
    # Ty le trung = trung / (ban ghi giu + trung): tinh tren doan da qua loc nhieu, khong tinh doan bi bo
    reached = stats["records"] + stats["dedup"]
    if reached and stats["dedup"] / reached >= DEDUP_WARN_RATIO:
        print(f"   [canh bao] {stats['dedup']}/{reached} doan trung (>= {DEDUP_WARN_RATIO:.0%}): kiem lai manifest")


def _process_one(source: Source) -> int:
    source_id = source.source_id
    raw_file = latest_raw_file(source_id)
    if raw_file is None:
        print(f"[{source_id}] chua co file tho: chay `python -m pipeline crawl-textbook --source {source_id}`",
              file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        records, stats = build_records(source, read_jsonl(raw_file), load_decisions(source_id))
    except ValueError as exc:  # file tho / decisions hong, hoac trim khong khop (thong bao co hash)
        print(f"loi: [{source_id}] {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    write_jsonl(processed_path(source_id), records)
    _print_stats(source, raw_file.name, stats)
    return EXIT_OK


def run_process_textbook(args: argparse.Namespace) -> int:
    check = load_checked_manifest()
    if check is None:
        return EXIT_INPUT_ERROR
    sources = select_sources(check, getattr(args, "source", None) or [])
    if sources is None:
        return EXIT_INPUT_ERROR
    if not sources:
        print("loi: khong co nguon status use de xu ly", file=sys.stderr)
        return EXIT_INPUT_ERROR
    return max(_process_one(source) for source in sources)
