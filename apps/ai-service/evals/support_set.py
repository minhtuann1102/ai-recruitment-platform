"""Phieu nguoi cham cho judge_support (Phase 05): 60 cap phan tang (45 `supported`, 15 `no_source`), an nhan cua
Evaluator va judge de khong bi moi. Phieu co noi dung tai lieu DE (giay phep chua chot) nen nam trong plans/reports,
khong commit; nhan luu o evals/support_labels/<rater>.json, khoa theo id.
  python -m evals.support_set export ../../plans/reports/judge-support-x.json --out ../../plans/reports/support-sheet.csv
  python -m evals.support_set import --rater rater_a ../../plans/reports/support-sheet.csv
  python -m evals.support_set agree ../../plans/reports/judge-support-x.json
"""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Dict, List

from app.rag.bm25_index import tokens
from evals.judge_support import unique
from evals.label_sheet import blind_id

LABELS_DIR = Path(__file__).with_name("support_labels")
QUOTA = {"supported": 45, "no_source": 15}
VERDICT = {"ung_ho": "entailed", "nguoc": "contradicted", "khong_lien_quan": "unrelated"}
SHEET_FIELDS = ["id", "question", "claim", "quote", "documents", "verdict", "note"]
MIN_AGREEMENT, MIN_KAPPA, MIN_LABELS = 0.8, 0.6, 30  # duoi nguong nay khong dung so cua judge


def sample(items: List[dict], seed: int = 7) -> List[dict]:
    rng, out = random.Random(seed), []
    pool = [i for i in unique(items) if i["docs"]]
    for support, quota in QUOTA.items():
        group = [i for i in pool if i["support"] == support]
        out += rng.sample(group, min(quota, len(group)))
    rng.shuffle(out)
    return out


def shown_doc(item: dict, result: dict) -> List[dict]:
    """Moi dong mot tai lieu (so tai lieu khong lo nhan): tai lieu judge da dung lam can cu, khong co thi tai lieu dau
    (`supported`) hoac tai lieu trung tu voi y nhat (`no_source`). Judge xet ca luot, nguoi xet mot tai lieu nen phieu
    co the lech o y co nhieu tai lieu ma judge tra `unrelated`."""
    named = [d for d in item["docs"] if d["id"] == (result or {}).get("doc_id")]
    words = set(tokens(item["claim"] + " " + item["quote"]))
    best = item["docs"][0] if item["support"] == "supported" else max(
        item["docs"], key=lambda d: len(words & set(tokens(d["text"]))))
    return named or [best]


def sheet_rows(items: List[dict], results: Dict[str, dict]) -> List[dict]:
    """Id mo: id that chua persona (junior-java-strong) lam lo muc chat luong."""
    return [{"id": blind_id(i["id"]), "question": i["question"], "claim": i["claim"], "quote": i["quote"],
             "documents": shown_doc(i, results.get(i["id"]))[0]["text"], "verdict": "", "note": ""} for i in items]


def parse_sheet(rows: List[dict]) -> Dict[str, str]:
    """Dong chua dien thi bo qua; gia tri la thi bao loi thay vi am tham mat nhan."""
    labels = {}
    for row in rows:
        value = row["verdict"].strip().lower()
        if value:
            if value not in VERDICT:
                raise ValueError(f"{row['id']}: verdict '{value}' phai la {sorted(VERDICT)}")
            labels[row["id"]] = VERDICT[value]
    return labels


def kappa(pairs: List[tuple]) -> float:
    """Cohen: ti le dong y da tru phan trung hop; judge luon tra `entailed` duoc ~0.7 ti le nhung kappa 0."""
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    chance = sum(left[k] * right[k] for k in left) / (n * n)
    return 0.0 if chance == 1 else (observed - chance) / (1 - chance)


def agreement(results: Dict[str, dict], labels: Dict[str, str]) -> Dict:
    judge = {blind_id(k): v["verdict"] for k, v in results.items() if v.get("verdict")}
    pairs = [(judge[i], v) for i, v in labels.items() if i in judge]
    if not pairs:
        return {"n": 0, "unmatched": len(labels), "usable": False}
    rate, k = sum(a == b for a, b in pairs) / len(pairs), kappa(pairs)
    per_class = {c: round(sum(a == c for a, b in pairs if b == c) / sum(b == c for _, b in pairs), 3)
                 for c in sorted({b for _, b in pairs})}
    return {"n": len(pairs), "unmatched": len(labels) - len(pairs), "agreement": round(rate, 3), "kappa": round(k, 3),
            "recall_by_human_label": per_class,
            "usable": len(pairs) >= MIN_LABELS and rate >= MIN_AGREEMENT and k >= MIN_KAPPA}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("report", type=Path)
    exp.add_argument("--out", type=Path, required=True)
    imp = sub.add_parser("import")
    imp.add_argument("sheet", type=Path)
    imp.add_argument("--rater", required=True)
    agr = sub.add_parser("agree")
    agr.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.cmd == "export":
        report = json.loads(args.report.read_text("utf-8"))
        rows = sheet_rows(sample(report["items"]), report["results"])
        with args.out.open("w", newline="", encoding="utf-8-sig") as f:  # BOM de Excel doc dung tieng Viet
            writer = csv.DictWriter(f, SHEET_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Da ghi {len(rows)} dong vao {args.out}")
    elif args.cmd == "import":
        with args.sheet.open(newline="", encoding="utf-8-sig") as f:
            labels = parse_sheet(list(csv.DictReader(f)))
        LABELS_DIR.mkdir(exist_ok=True)
        (LABELS_DIR / f"{args.rater}.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1), "utf-8")
        print(f"Da nhap {len(labels)} nhan")
    else:
        results = json.loads(args.report.read_text("utf-8"))["results"]
        for path in sorted(LABELS_DIR.glob("*.json")):
            print(path.stem, agreement(results, json.loads(path.read_text("utf-8"))))


if __name__ == "__main__":
    main()
