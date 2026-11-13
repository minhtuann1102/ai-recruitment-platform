"""Lenh relabel-apply (Phase B, FR-028): gop judgments cua model da chon + duyet crawl 27/10 + qa-drops.json thanh
data/raw/relabel/decisions.json. Offline, khong can key. Sau do validate / process / index tu ap file nay.

Chi dung dong judgments hop le (qua lai parse_judgment, ke ca dong do subagent viet) va con dung (cung prompt_version,
cham tren dung topic hien tai); bao so cap crawl chua co nhan dung de chay them relabel truoc khi index.
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from .qa_relabel_agreement import REVIEW_CSV
from .qa_relabel_command import cache_path, crawled_pairs, is_current, read_cache
from .qa_relabel_decisions import (DECISIONS_PATH, DROPS_PATH, build_decisions, default_golden_files, golden_qa_ids,
                                   read_review_csv, write_decisions)
from .qa_relabel_prompt import PROMPT_VERSION, parse_judgment
from .qa_seed_loader import SeedError
from .topic_catalog_reader import CatalogError

NO_REVIEW = "none"


def usable_judgments(rows: Dict[str, Dict], pairs: List[Dict], topic_ids: set) -> Tuple[Dict[str, Dict], Counter]:
    """Loc dong judgments: hop le theo parse_judgment va con dung voi nhan goc hien tai cua cap."""
    by_id = {p["qa_id"]: p for p in pairs}
    usable, stats = {}, Counter()
    for qa, row in rows.items():
        pair = by_id.get(qa)
        if pair is None:
            stats["judgment_khong_con_cap"] += 1
            continue
        if not is_current(row, pair):
            stats["judgment_cu"] += 1
            continue
        judgment, reason = parse_judgment(json.dumps(row, ensure_ascii=False), pair["topic_id"], topic_ids)
        if judgment is None:
            stats[f"judgment_hong:{reason}"] += 1
            continue
        usable[qa] = {**judgment, "model": row.get("model", "?"), "topic_before": pair["topic_id"]}
    stats["cap_crawl_chua_co_nhan"] = len(set(by_id) - set(usable))
    return usable, stats


def summarize(decisions: dict) -> Counter:
    stats: Counter = Counter()
    for d in decisions.values():
        if "drop" in d:
            stats["drop:" + d["drop"].split(":", 1)[0]] += 1
            continue
        stats["topic_changed"] += "topic_id" in d
        stats["interview_style_false"] += d.get("interview_style") is False
        stats["golden_kept"] += "golden_kept" in d
    return stats


def run_relabel_apply(args: argparse.Namespace) -> int:
    rows = read_cache(cache_path(args.model))
    if not rows:
        print(f"loi: chua co judgments cho model {args.model} ({cache_path(args.model)}); chay relabel truoc",
              file=sys.stderr)
        return 1
    review_path = Path(args.review_csv)
    if args.review_csv != NO_REVIEW and not review_path.exists():
        print(f"loi: khong thay {review_path} (duyet crawl 27/10, nam ngoai git). Chay merge_crawl_reviews.py, hoac "
              f"--review-csv {NO_REVIEW} neu co y bo qua 52 drop + do kho cua dot duyet do", file=sys.stderr)
        return 1
    try:
        de_drops = json.loads(DROPS_PATH.read_text(encoding="utf-8-sig")) if DROPS_PATH.exists() else {}
        pairs, topics = crawled_pairs([])
    except (json.JSONDecodeError, CatalogError, SeedError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return 1
    judgments, judged_stats = usable_judgments(rows, pairs, {t["id"] for t in topics})
    reviews = read_review_csv(review_path) if args.review_csv != NO_REVIEW else {}
    protected = golden_qa_ids(default_golden_files())
    decisions = build_decisions(judgments, reviews, de_drops, protected)
    meta = {"model": args.model, "prompt_version": PROMPT_VERSION, "judged": len(judgments),
            "review_rows": len(reviews), "de_drops": len(de_drops), "golden_protected": len(protected)}
    path = write_decisions(decisions, meta, DECISIONS_PATH)
    print(f"== relabel-apply: {dict(sorted(summarize(decisions).items()))}; {dict(sorted(judged_stats.items()))}")
    print(f"   {meta} -> {path}")
    golden = sorted(qa for qa, d in decisions.items() if "golden_kept" in d)
    if golden:
        print(f"   cap golden dang dung bi de xuat bo, GIU NGUYEN, DE xu ly tay: {', '.join(golden)}")
    if judged_stats["cap_crawl_chua_co_nhan"]:
        print(f"   canh bao: {judged_stats['cap_crawl_chua_co_nhan']} cap crawl chua co nhan dung -> giu nhan enrich; "
              f"chay relabel cho het truoc khi index")
    print("   enriched_qa/ khong doi (ban sao luu). Kiem: python -m pipeline validate; xoa file tren de ve nhan cu.")
    return 0


def add_parser(sub) -> None:
    apply = sub.add_parser("relabel-apply", help="gop ket qua relabel + duyet 27/10 + qa-drops -> decisions.json")
    apply.add_argument("--model", default=os.getenv("RELABEL_MODEL", "gpt-6-luna"),
                       help="model da chon (ten trong judgments-<model>.jsonl); mac dinh RELABEL_MODEL")
    apply.add_argument("--review-csv", default=str(REVIEW_CSV), metavar="FILE",
                       help=f"decisions-all.csv cua duyet 27/10; '{NO_REVIEW}' de bo qua")
