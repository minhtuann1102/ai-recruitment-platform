"""coverage-textbook (spec 012 T032, data-model §5, contract pipeline-cli-textbook): bao cao do phu + kiem tra truy hoi.

Doc moi file da xu ly cua cac nguon trong manifest, tinh bao cao (textbook_coverage_report), ghi
`TEXTBOOK_PROCESSED_DIR/coverage-report.json`, in bang + gaps. Offline; `--db` them kiem tra vector tren kho that (can .env).
Luon thoat 0 khi chay duoc (cho thieu nam trong gaps); `--strict` thoat 1 khi khong dat SC-001 hoac SC-004;
--db loi cau hinh / DB -> 2.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg

from . import settings
from .knowledge_chunk_writer import PreflightError
from .textbook_coverage_report import build_report, drop_reasons, scenario_queries
from .textbook_coverage_vector_check import run_vector_check
from .textbook_command_common import load_checked_manifest
from .textbook_processed_jsonl_reader import read_processed
from .textbook_review_decisions import load_decisions
from .settings import ConfigError

REPORT_FILE = "coverage-report.json"
EXIT_OK, EXIT_INPUT_ERROR, EXIT_PREFLIGHT_ERROR = 0, 1, 2


def _pct(value: Optional[float]) -> str:
    return "-" if value is None else f"{value:.0%}"


def format_report(report: Dict[str, Any]) -> List[str]:
    lines = ["== nguon x giay phep x doan",
             f"{'source':<24}{'status':<10}{'license':<26}{'class':<12}{'trang':>6}{'doan':>6}  drop theo ly do"]
    for s in report["sources"]:
        drops = ", ".join(f"{k} {v}" for k, v in s["drops"].items()) or "-"
        lines.append(f"{s['source_id']:<24}{s['status']:<10}{s['license'] or '-':<26}{s['license_class'] or '-':<12}"
                     f"{s['pages_used']:>6}{s['chunks']:>6}  {drops}")
    lines += ["== track", f"{'track':<18}{'official':>9}{'doan':>7}"]
    lines += [f"{t:<18}{r['official_sources']:>9}{r['chunks']:>7}" for t, r in report["tracks"].items()]
    with_vector = report["totals"]["vector_hit_ratio"] is not None
    lines += ["== tinh huong", f"{'scenario':<42}{'doan':>6}{'tu khoa':>9}" + (f"{'vector':>8}" if with_vector else "")]
    for scn, r in report["scenarios"].items():
        keyword = f"#{r['first_hit_rank']}" if r["keyword_hit"] else "miss"
        vector = f"{'hit' if r['vector_hit'] else 'miss':>8}" if with_vector else ""
        lines.append(f"{scn:<42}{r['chunks']:>6}{keyword:>9}{vector}")
    labels = {"zero_chunks": "0 doan", "under_3_chunks": "duoi 3 doan", "retrieval_miss": "truot tu khoa",
              "vector_miss": "truot vector"}
    lines.append("== gaps")
    for key, scenarios in report["gaps"].items():
        lines.append(f"   {labels[key]} ({len(scenarios)}): {', '.join(scenarios) or '-'}")
    t = report["totals"]
    lines.append(f"== tong: {t['chunks']} doan, {t['scenarios']} tinh huong; >=1 doan {_pct(t['ratio_ge1'])}, "
                 f">=3 doan {_pct(t['ratio_ge3'])}, trung tu khoa {_pct(t['keyword_hit_ratio'])}, "
                 f"trung vector {_pct(t['vector_hit_ratio'])}")
    lines.append(f"   SC-001: {'dat' if t['sc001'] else 'KHONG DAT'}; SC-004: {'dat' if t['sc004'] else 'KHONG DAT'}")
    return lines


def run_coverage_textbook(args: argparse.Namespace) -> int:
    check = load_checked_manifest()
    if check is None:
        return EXIT_INPUT_ERROR
    records_by_source: Dict[str, List[Dict]] = {}
    drops: Dict[str, Dict[str, int]] = {}
    try:
        for source in check.sources:
            try:
                records_by_source[source.source_id] = read_processed(source.source_id)
            except FileNotFoundError:
                continue  # nguon chua xu ly: 0 doan
            drops[source.source_id] = drop_reasons(load_decisions(source.source_id).decisions)
    except ValueError as exc:  # file xu ly / decisions hong
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    known = {s.source_id for s in check.sources}
    for path in sorted(Path(settings.TEXTBOOK_PROCESSED_DIR).glob("*.jsonl")):
        if path.stem not in known:
            print(f"canh bao: {path.name} khong thuoc nguon nao trong manifest (bo qua)", file=sys.stderr)
    vector_hits = None
    if getattr(args, "db", False):
        try:
            vector_hits = run_vector_check(scenario_queries(check.tracks, check.queries))
        except (ConfigError, PreflightError, psycopg.OperationalError) as exc:
            print(f"loi preflight: {exc}", file=sys.stderr)
            return EXIT_PREFLIGHT_ERROR
    report = build_report(check.sources, check.tracks, check.queries, records_by_source, drops, vector_hits)
    out = Path(settings.TEXTBOOK_PROCESSED_DIR) / REPORT_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(format_report(report)))
    print(f"   -> {out}")
    totals = report["totals"]
    if getattr(args, "strict", False) and not (totals["sc001"] and totals["sc004"]):
        print("loi: --strict: khong dat SC-001 hoac SC-004 (xem gaps)", file=sys.stderr)
        return EXIT_INPUT_ERROR
    return EXIT_OK
