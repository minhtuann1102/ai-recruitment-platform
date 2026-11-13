"""Lenh scope-check-score (spec 005 FR-030, T067): doc lo + judgments, goi build_report (qa_scope_check_report), ghi bao cao
JSON va in tom tat. Offline, khong goi LLM.

Dong judgments sai khong lam hong lenh: vao `errors`, item thanh `missing` cua judge. Bao cao luon duoc ghi truoc; thoat 1
khi co errors HOAC cham chua day du (item that / item cai chua duoc moi judge cham, `complete` = false).
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .qa_scope_check_judgments import load_batch_items, load_manifest_ids, read_judgments
from .qa_scope_check_points import ScopeCheckError
from .qa_scope_check_report import build_report


def _read_object(path: Optional[str], name: str) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScopeCheckError(f"khong doc duoc {name} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ScopeCheckError(f"{name} {path}: phai la object JSON {{item_id: ...}}")
    return data


def _ratio(value: Optional[float]) -> str:
    return "-" if value is None else f"{value:.0%}"


def format_summary(report: Dict[str, Any]) -> str:
    lines = [f"== scope-check-score: {report['items']} item that, judge: {', '.join(report['judges']) or '-'}; "
             f"co {report['flagged']} (moi judge dong y: {report['flagged_all_judges']}); "
             f"chua judge nao cham: {len(report['unjudged'])}"]
    canaries = report["canaries"]
    for judge, c in (canaries["caught"].items() if canaries["count"] else ()):
        lines.append(f"   cau moi {judge}: bat {c['caught']}/{c['judged']} (tong {canaries['count']})")
    calibration = report["calibration"]
    for name, c in [*calibration.get("judges", {}).items(), ("union", calibration.get("union"))]:
        if c:
            lines.append(f"   hieu chinh {name}: recall {_ratio(c['recall'])}, precision {_ratio(c['precision'])} "
                         f"(tp {c['tp']}, fp {c['fp']}, fn {c['fn']}, tn {c['tn']})")
    for judge, ids in report["missing"].items():
        extra = canaries["missing"].get(judge, [])
        if ids or extra:
            lines.append(f"   thieu {judge}: {len(ids)} item that, {len(extra)} item cai chua cham hop le")
    lines.append(f"   errors: {len(report['errors'])}; day du: {'co' if report['complete'] else 'KHONG'}")
    return "\n".join(lines)


def run_scope_check_score(args: argparse.Namespace) -> int:
    try:
        batches_dir = Path(args.batches_dir)
        items = load_batch_items(batches_dir)
        manifest_ids = load_manifest_ids(batches_dir)
        found = read_judgments([Path(p) for p in args.judgments], items)
        report = build_report(items, manifest_ids, found, _read_object(args.canary_key, "canary-key"),
                              _read_object(args.truth, "truth"))
    except ScopeCheckError as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(format_summary(report))
    for error in report["errors"][:10]:
        print(f"   ! {error}", file=sys.stderr)
    print(f"   -> {out}")
    return 1 if report["errors"] or not report["complete"] else 0


def add_parser(sub) -> None:
    score = sub.add_parser("scope-check-score", help="gop judgments ra soat y dap an ngoai cau hoi thanh bao cao")
    score.add_argument("--batches-dir", required=True, metavar="DIR",
                       help="thu muc batch-NN.json + manifest.json cua scope-check-prepare (co the them file lo chua canary)")
    score.add_argument("--judgments", action="append", required=True, metavar="FILE", help="file .jsonl (lap lai duoc)")
    score.add_argument("--canary-key", metavar="FILE", help="JSON {item_id: [id y cai]}")
    score.add_argument("--truth", metavar="FILE", help="JSON {item_id: true|false (can sua)} de tinh recall / precision")
    score.add_argument("--out", required=True, metavar="FILE", help="bao cao JSON")
