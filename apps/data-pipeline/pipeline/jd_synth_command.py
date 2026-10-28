"""Lenh synth-jd [--target 500] [--limit N] [--dry-run] (spec 009 US5, contracts/pipeline-cli-jd.md).

Doc bao cao process-jd moi nhat -> ke hoach o thieu (jd_gap_planner) -> sinh JD synthetic (jd_synthetic_generator)
-> data/raw/jd/synthetic/<UTC ts>.jsonl (sap theo source_job_id, khoa sap, newline '\\n').
So thu tu n cua moi o danh tiep tu so lon nhat da co trong synthetic/ (JD bi process-jd loai -> lan sau so moi).
Ma thoat: 0; 1 chua co bao cao, hoac file synthetic moi nhat khong cu hon bao cao (chay process-jd truoc);
2 thieu key (truoc moi loi goi); 3 con JD loi sau retry.
"""
import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, TextIO, Tuple

from .jd_gap_planner import GapPlan, plan_gaps
from .jd_process_command import RawReadError, read_raw_records
from .jd_record_builder import is_synthetic
from .jd_synthetic_generator import CompleteFn, SynthOutcome, generate_one
from .settings import JD_RAW_DIR, PROCESSED_DIR, SKILL_DICTIONARY_PATH, ConfigError, require_llm_settings
from .skill_dictionary import SkillDictionaryError, load_skill_dictionary

EXIT_OK, EXIT_INPUT_ERROR, EXIT_NO_KEY, EXIT_FAILED = 0, 1, 2, 3
SYNTHETIC_DIRNAME = "synthetic"
WORKERS = 8
PRICE_IN, PRICE_OUT = 0.15, 0.60  # USD / 1M token gpt-4o-mini, chi de uoc tinh (SC-008)
_TS_RE = re.compile(r"\d{8}T\d{6}Z")
_ID_RE = re.compile(r"^syn-(?P<cell>.+)-(?P<n>\d+)$")

Cell = Tuple[str, str, str]


def _stamp(path: Path) -> str:
    match = _TS_RE.search(path.name)
    return match.group(0) if match else ""


def latest_report(processed_dir: Path) -> Optional[Path]:
    reports = sorted(processed_dir.glob("jd-report-*.json"), key=_stamp)
    return reports[-1] if reports else None


def synthetic_files(raw_dir: Path) -> List[Path]:
    return sorted((raw_dir / SYNTHETIC_DIRNAME).glob("*.jsonl"), key=_stamp)


def existing_numbers(raw_dir: Path) -> Dict[str, int]:
    """'group-level-city' -> n lon nhat da co trong synthetic/*.jsonl."""
    numbers: Dict[str, int] = {}
    for path in synthetic_files(raw_dir):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _ID_RE.match(str(json.loads(line).get("source_job_id") or "")) if line.strip() else None
            if match:
                numbers[match["cell"]] = max(numbers.get(match["cell"], 0), int(match["n"]))
    return numbers


def crawl_companies(raw_dir: Path) -> Set[str]:
    try:
        return {str(r.get("company") or "") for r in read_raw_records(raw_dir) if not is_synthetic(r)}
    except RawReadError:
        return set()


def schedule(plan: GapPlan, numbers: Dict[str, int], limit: Optional[int]) -> List[Tuple[Cell, int]]:
    """(o, n) can sinh, xen ke theo vong (JD thu k cua moi o) de --limit nho van rai nhieu o; cat o limit."""
    rounds: List[List[Tuple[Cell, int]]] = []
    for row in plan.cells:
        cell = (row["group"], row["level"], row["city"])
        start = numbers.get("-".join(cell), 0)
        for k in range(row["add"]):
            if len(rounds) <= k:
                rounds.append([])
            rounds[k].append((cell, start + k + 1))
    jobs = [job for batch in rounds for job in batch]
    return jobs[:limit] if limit is not None else jobs


def print_plan(plan: GapPlan, out: Optional[TextIO] = None) -> None:
    out = out or sys.stdout
    print(f"== synth-jd: jd_out {plan.valid}, bu so luong {plan.need_total}, bu san {plan.floor_added}, "
          f"tong {plan.total} JD / {len(plan.cells)} o", file=out)
    for row in plan.cells:
        print(f"  {row['group']:<16} {row['level']:<8} {row['city']:<12} co {row['current']:>3}  +{row['add']}", file=out)


def write_synthetic(raw_dir: Path, records: List[Dict], now: datetime) -> Path:
    path = raw_dir / SYNTHETIC_DIRNAME / f"{now:%Y%m%dT%H%M%SZ}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(records, key=lambda r: r["source_job_id"])
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def _print_outcomes(outcomes: List[SynthOutcome]) -> None:
    per_cell: Dict[str, Counter] = {}
    for o in outcomes:
        per_cell.setdefault(_ID_RE.match(o.source_job_id)["cell"], Counter())["ok" if o.record else "failed"] += 1
    for cell, counts in sorted(per_cell.items()):
        print(f"  {cell:<40} sinh {counts['ok']}  loi {counts['failed']}")
    for o in outcomes:
        if o.record is None:
            print(f"[loi] {o.source_job_id}: {' | '.join(o.reasons)}", file=sys.stderr)
    tokens_in, tokens_out = sum(o.tokens_in for o in outcomes), sum(o.tokens_out for o in outcomes)
    cost = (tokens_in * PRICE_IN + tokens_out * PRICE_OUT) / 1_000_000
    print(f"loi goi LLM {sum(o.calls for o in outcomes)}, token {tokens_in} vao / {tokens_out} ra, ~{cost:.4f} USD")


def synth_jd(args: argparse.Namespace, make_complete: Callable[[], CompleteFn], now: datetime,
             raw_dir: Path, processed_dir: Path, dictionary_path: Path) -> int:
    report_path = latest_report(processed_dir)
    if report_path is None:
        print(f"[loi] chua co bao cao jd-report-*.json trong {processed_dir} (chay process-jd truoc)", file=sys.stderr)
        return EXIT_INPUT_ERROR
    synth = synthetic_files(raw_dir)
    if synth and _stamp(synth[-1]) >= _stamp(report_path):
        print(f"[loi] {synth[-1].name} khong cu hon {report_path.name}: chay process-jd truoc", file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        dictionary = load_skill_dictionary(dictionary_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (SkillDictionaryError, OSError, ValueError) as exc:
        print(f"[loi] {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    plan = plan_gaps(report, target=args.target)
    print_plan(plan)
    if args.dry_run:
        return EXIT_OK
    try:
        complete = make_complete()
    except ConfigError as exc:
        print(f"[loi] {exc}", file=sys.stderr)
        return EXIT_NO_KEY
    jobs = schedule(plan, existing_numbers(raw_dir), args.limit)
    if not jobs:
        print("khong con o thieu: 0 loi goi LLM")
        return EXIT_OK
    companies = crawl_companies(raw_dir)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        outcomes = list(pool.map(lambda job: generate_one(*job, dictionary, complete, companies, now), jobs))
    _print_outcomes(outcomes)
    records = [o.record for o in outcomes if o.record]
    if records:
        print(f"-> {write_synthetic(raw_dir, records, now)} ({len(records)} JD)")
    return EXIT_FAILED if len(records) < len(outcomes) else EXIT_OK


def _llm_complete() -> CompleteFn:
    from .llm_enricher import LlmClient  # import cham: --dry-run khong can openai / key

    return LlmClient(require_llm_settings()).complete


def run_synth_jd(args: argparse.Namespace) -> int:
    return synth_jd(args, _llm_complete, datetime.now(timezone.utc), JD_RAW_DIR, PROCESSED_DIR, SKILL_DICTIONARY_PATH)
