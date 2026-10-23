"""Lenh review-sample: lay mau ngau nhien cap da dich moi nguon de nguoi duyet doc doi chieu ban goc.

Hai dau ra (spec 005 Clarifications 2026-10-19: review theo mau):
- data/processed/review-sample.txt: ban goc canh ban dich (co noi dung -> gitignore).
- data/reviews/translation-review.csv: cid, nguon, ket luan, nguoi duyet (khong noi dung -> commit duoc).
Nguoi duyet dien cot verdict (ok | bad) va reviewer trong CSV. Chay lai chi lay them cap chua co trong CSV.
"""
import argparse
import csv
import json
import random
from pathlib import Path
from typing import Dict, List, Set

from .settings import APP_DIR, ENRICHED_DIR, PROCESSED_DIR

REVIEW_FILE = APP_DIR / "data" / "reviews" / "translation-review.csv"
SHEET_FILE = PROCESSED_DIR / "review-sample.txt"
FIELDS = ["cid", "source", "topic_id", "difficulty", "verdict", "reviewer", "note"]
MAX_ANSWER_CHARS_SHOWN = 1200


def _reviewed_ids(review_file: Path) -> Set[str]:
    if not review_file.exists():
        return set()
    with review_file.open(encoding="utf-8", newline="") as handle:
        return {row["cid"] for row in csv.DictReader(handle)}


def sample_pairs(enriched_dir: Path, per_source: int, seed: int, skip: Set[str]) -> Dict[str, List[Dict]]:
    """Mau co dinh theo seed; moi nguon toi da per_source cap chua duyet."""
    rng = random.Random(seed)
    samples: Dict[str, List[Dict]] = {}
    for path in sorted(enriched_dir.glob("*.json")):
        candidates = [p for p in json.loads(path.read_text(encoding="utf-8")) if p["qa_id"] not in skip]
        if candidates:
            samples[path.stem] = rng.sample(candidates, min(per_source, len(candidates)))
    return samples


def _sheet_entry(number: int, source: str, pair: Dict) -> str:
    return (
        f"=== [{number}] {pair['qa_id']} | {source} | {pair['topic_id']} | {pair['difficulty']} | goc: {pair.get('source_lang', '?')}\n"
        f"Q goc: {pair.get('question_original', '')}\n"
        f"Q vi : {pair['question']}\n"
        f"--- A goc:\n{pair.get('answer_original', '')[:MAX_ANSWER_CHARS_SHOWN]}\n"
        f"--- A vi:\n{pair['answer'][:MAX_ANSWER_CHARS_SHOWN]}\n"
    )


def write_review_files(samples: Dict[str, List[Dict]], review_file: Path, sheet_file: Path) -> int:
    rows, entries = [], []
    for source, pairs in samples.items():
        for pair in pairs:
            entries.append(_sheet_entry(len(entries) + 1, source, pair))
            rows.append({"cid": pair["qa_id"], "source": source, "topic_id": pair["topic_id"], "difficulty": pair["difficulty"],
                         "verdict": "", "reviewer": "", "note": ""})
    sheet_file.parent.mkdir(parents=True, exist_ok=True)
    sheet_file.write_text("\n".join(entries), encoding="utf-8")
    review_file.parent.mkdir(parents=True, exist_ok=True)
    new_file = not review_file.exists()
    with review_file.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def run_review_sample(args: argparse.Namespace) -> int:
    samples = sample_pairs(ENRICHED_DIR, args.per_source, args.seed, _reviewed_ids(REVIEW_FILE))
    count = write_review_files(samples, REVIEW_FILE, SHEET_FILE)
    print(f"lay {count} cap tu {len(samples)} nguon")
    print(f"doc: {SHEET_FILE}")
    print(f"ghi ket luan (verdict = ok | bad, reviewer): {REVIEW_FILE}")
    return 0
