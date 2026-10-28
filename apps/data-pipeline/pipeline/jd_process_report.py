"""Bao cao process-jd (spec 009 research R8, contracts/pipeline-cli-jd.md "Thong ke process-jd", constitution V).

Ham thuan: tu raw da doc + BuildResult + chunk -> dict bao cao (khoa sap, gia tri deterministic) va ban in man hinh.
cells: so JD crawl / synthetic theo (group, level, city), chi JD co du ca ba truong (Gap Cell cua US5).
"""
import sys
from collections import Counter
from typing import Dict, Iterable, List, Optional, TextIO

from .jd_pii import count_jd_pii
from .jd_record_builder import REJECT_DUPLICATE, REJECT_REASONS, is_synthetic
from .jd_record_dedup import BuildResult

UNKNOWN = "unknown"  # gia tri null trong distribution (khoa JSON khong the la null)
TOP_UNKNOWN_SKILLS = 50
DISTRIBUTION_FIELDS = ("group", "level", "city", "work_type")


def _ratio(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def _source(jd_id: str) -> str:
    return jd_id.split(":", 1)[0]


def count_output_pii(records: Iterable[Dict], chunks: Iterable[Dict]) -> int:
    """PII con lai tren moi truong chu cua output (pii_remaining, FR-009); phai = 0."""
    total = 0
    for record in records:
        texts = [record["title"], record["company"], *record["sections"].values(), *record["skills_unknown"]]
        total += sum(count_jd_pii(text) for text in texts)
    return total + sum(count_jd_pii(chunk["content"]) for chunk in chunks)


def _cells(records: List[Dict]) -> List[Dict]:
    counts: Dict[tuple, Counter] = {}
    for r in records:
        if r["group"] and r["level"] and r["city"]:
            counts.setdefault((r["group"], r["level"], r["city"]), Counter())["synthetic" if r["synthetic"] else "crawled"] += 1
    return [
        {"group": g, "level": lv, "city": c, "crawled": n["crawled"], "synthetic": n["synthetic"]}
        for (g, lv, c), n in sorted(counts.items())
    ]


def _unknown_skills(records: List[Dict]) -> List[Dict]:
    counts = Counter(name.lower() for r in records for name in r["skills_unknown"])
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TOP_UNKNOWN_SKILLS]
    return [{"name": name, "count": n} for name, n in top]


def build_report(raws: List[Dict], result: BuildResult, chunks: List[Dict], pii_remaining: int) -> Dict:
    records = result.records
    crawl = [r for r in records if not r["synthetic"]]
    synthetic_out = len(records) - len(crawl)
    by_reason = Counter(r["reason"] for r in result.rejected)
    rejected_by_source: Dict[str, Counter] = {}
    for r in result.rejected:
        rejected_by_source.setdefault(_source(r["jd_id"]), Counter())[r["reason"]] += 1
    synthetic_in = sum(1 for raw in raws if is_synthetic(raw))
    duplicates = by_reason[REJECT_DUPLICATE]
    return {
        "records_in": {
            "crawl": len(raws) - synthetic_in,
            "synthetic": synthetic_in,
            "by_source": dict(sorted(Counter(str(raw.get("source") or "") for raw in raws).items())),
        },
        "rejected": {reason: by_reason[reason] for reason in REJECT_REASONS},
        "rejected_by_source": {s: dict(sorted(c.items())) for s, c in sorted(rejected_by_source.items())},
        "jd_out": len(records),
        "dedup_ratio": _ratio(duplicates, len(records) + duplicates),
        "chunks_out": len(chunks),
        "with_skill_ratio": _ratio(sum(1 for r in crawl if r["skills"]), len(crawl)),
        "crawl_vs_synthetic": {
            "crawl": len(crawl), "synthetic": synthetic_out, "synthetic_ratio": _ratio(synthetic_out, len(records)),
        },
        "distribution": {
            f: dict(sorted(Counter(r[f] or UNKNOWN for r in records).items())) for f in DISTRIBUTION_FIELDS
        },
        "unknown_skills": _unknown_skills(records),
        "near_duplicates": result.near_duplicates,
        "pii_remaining": pii_remaining,
        "cells": _cells(records),
    }


def print_report(report: Dict, stream: Optional[TextIO] = None) -> None:
    out = stream or sys.stdout
    print("== process-jd: thong ke", file=out)
    for key in ("records_in", "rejected", "jd_out", "dedup_ratio", "chunks_out", "with_skill_ratio",
                "crawl_vs_synthetic", "pii_remaining"):
        print(f"{key:<19} {report[key]}", file=out)
    for field in DISTRIBUTION_FIELDS:
        print(f"distribution.{field:<6} {report['distribution'][field]}", file=out)
    top = ", ".join(f"{s['name']} ({s['count']})" for s in report["unknown_skills"][:20])
    print(f"unknown_skills      {top or '-'}", file=out)
    print(f"cells               {len(report['cells'])} o (group, level, city)", file=out)
    if report["near_duplicates"]:
        print(f"[canh bao] {len(report['near_duplicates'])} nhom trung gan dung (cung cong ty + tieu de):", file=out)
        for ids in report["near_duplicates"][:20]:
            print(f"  - {', '.join(ids)}", file=out)
