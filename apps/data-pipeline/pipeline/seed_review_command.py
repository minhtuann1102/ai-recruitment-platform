"""Duyet seed curated: xuat cap chua co reviewed_by de doc, roi danh dau cap da doc.

- review-seed: ghi data/processed/seed-review.txt (cau hoi, dap an, grounding_urls) cho moi cap chua duyet.
- approve-seed --reviewer NAME --ids de-qa-1000..1021,de-qa-1050: dien reviewed_by cho dung cac cap do.
  Chi danh dau cap nguoi duyet da doc that (spec 005 FR-003); cap sai thi sua hoac xoa tay trong file JSON.
"""
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Set

from .settings import PROCESSED_DIR, SEEDS_DIR

SHEET_FILE = PROCESSED_DIR / "seed-review.txt"
_RANGE_RE = re.compile(r"^de-qa-(\d{4})\.\.(?:de-qa-)?(\d{4})$")


def parse_ids(spec: str) -> Set[str]:
    """'de-qa-1000..1003,de-qa-1050' -> {de-qa-1000, ..., de-qa-1003, de-qa-1050}."""
    ids: Set[str] = set()
    for part in filter(None, (p.strip() for p in spec.split(","))):
        match = _RANGE_RE.match(part)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            ids.update(f"de-qa-{n:04d}" for n in range(start, end + 1))
        elif re.match(r"^de-qa-\d{4}$", part):
            ids.add(part)
        else:
            raise ValueError(f"id khong hop le: {part}")
    return ids


def _load(path: Path) -> List[Dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def unreviewed_pairs(seeds_dir: Path = SEEDS_DIR) -> List[Dict]:
    return [
        dict(pair, _file=path.name)
        for path in sorted(seeds_dir.glob("*.json"))
        for pair in _load(path)
        if isinstance(pair, dict) and not str(pair.get("reviewed_by", "")).strip()
    ]


def approve(ids: Set[str], reviewer: str, seeds_dir: Path = SEEDS_DIR) -> Set[str]:
    """Dien reviewed_by cho cac qa_id trong ids; tra ve cac id da danh dau."""
    approved: Set[str] = set()
    for path in sorted(seeds_dir.glob("*.json")):
        pairs = _load(path)
        changed = False
        for pair in pairs:
            if isinstance(pair, dict) and pair.get("qa_id") in ids:
                pair["reviewed_by"] = reviewer
                approved.add(pair["qa_id"])
                changed = True
        if changed:
            path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return approved


def run_review_seed(args: argparse.Namespace) -> int:
    pairs = unreviewed_pairs()
    blocks = [
        f"=== {p['qa_id']} | {p['_file']} | {p.get('topic_id')} | {p.get('difficulty')}\n"
        f"Q: {p.get('question', '')}\n--- A:\n{p.get('answer', '')}\n"
        f"--- nguon: {', '.join(p.get('grounding_urls', [])) or p.get('source', '')}\n"
        for p in pairs
    ]
    SHEET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SHEET_FILE.write_text("\n".join(blocks), encoding="utf-8")
    print(f"{len(pairs)} cap chua duyet -> {SHEET_FILE}")
    return 0


def run_approve_seed(args: argparse.Namespace) -> int:
    try:
        ids = parse_ids(args.ids)
    except ValueError as exc:
        print(f"loi: {exc}")
        return 1
    approved = approve(ids, args.reviewer)
    missing = sorted(ids - approved)
    print(f"danh dau {len(approved)} cap reviewed_by={args.reviewer}")
    if missing:
        print(f"khong tim thay: {', '.join(missing)}")
    return 1 if missing else 0
