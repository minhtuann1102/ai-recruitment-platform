"""Phieu gan nhan golden set Evaluator cho nguoi cham doc lap (docs/ai-service/09 muc 10.2).

Xuat CSV KHONG co intended_tier / adversarial (tranh nguoi cham bi moi), nguoi cham dien 4 band + answer_type,
roi nhap lai thanh evals/evaluator_labels/<rater>.json.
  python -m evals.label_sheet export --out /tmp/sheet_a.csv
  python -m evals.label_sheet import --rater rater_a /tmp/sheet_a.csv
"""
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Dict, List

from evals.evaluator_metrics import CRITERIA

GOLDEN = Path(__file__).with_name("evaluator_golden.jsonl")
LABELS_DIR = Path(__file__).with_name("evaluator_labels")
ANSWER_TYPES = {"answered", "partial", "dont_know", "off_topic", "asks_clarification", "manipulation"}
SHEET_FIELDS = ["id", "level", "phase", "turn_kind", "question", "key_points", "answer", *CRITERIA, "answer_type", "note"]


def load_golden(path: Path = GOLDEN) -> List[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def blind_id(sample_id: str) -> str:
    """Id mo tren phieu: id that ("q01-strong", "a01-injection-...") lam lo muc chat luong cho nguoi cham."""
    return "s" + hashlib.sha1(sample_id.encode("utf-8")).hexdigest()[:8]


def needs_label(sample: dict) -> bool:
    """Mau injection da co ky vong theo dinh nghia (FR-AI-032), khong can nguoi cham."""
    return "answer_type" not in sample.get("expect", {})


def export_sheet(samples: List[dict], out: Path, seed: int = 7) -> None:
    rows = [s for s in samples if needs_label(s)]
    random.Random(seed).shuffle(rows)  # tron thu tu de cac muc chat luong cua mot cau hoi khong dung canh nhau
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        writer.writeheader()
        for s in rows:
            writer.writerow({"id": blind_id(s["id"]), "level": s["level"], "phase": s["phase"], "turn_kind": s["turn_kind"],
                             "question": s["question"], "key_points": " | ".join(s["topic"]["key_points"]),
                             "answer": s["answer"]})


def parse_sheet(path: Path, known_ids: set) -> Dict[str, dict]:
    """Doc CSV da dien (id mo -> id that); bo qua dong trong; dong sai gia tri hoac trung id thi bao loi."""
    labels, errors = {}, []
    real = {blind_id(i): i for i in known_ids}
    with path.open(encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel/Sheets hay them BOM
        for row in csv.DictReader(f):
            sid = real.get(row["id"].strip(), row["id"].strip())
            values = [row.get(c, "").strip() for c in CRITERIA]
            atype = row.get("answer_type", "").strip()
            if not any(values) and not atype:
                continue
            if sid not in known_ids:
                errors.append(f"{sid}: id khong co trong golden set")
            elif sid in labels:
                errors.append(f"{row['id']}: id bi trung trong phieu")
            elif not all(v.isdigit() and 0 <= int(v) <= 4 for v in values) or atype not in ANSWER_TYPES:
                errors.append(f"{row['id']}: band phai la so nguyen 0-4 va answer_type hop le")
            else:
                labels[sid] = {**{c: int(v) for c, v in zip(CRITERIA, values)}, "answer_type": atype}
    if errors:
        raise ValueError("Phieu sai:\n" + "\n".join(errors))
    return labels


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("--out", type=Path, required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--rater", required=True)
    imp.add_argument("sheet", type=Path)
    args = parser.parse_args()
    samples = load_golden()
    if args.cmd == "export":
        export_sheet(samples, args.out)
        print(f"Da xuat {sum(needs_label(s) for s in samples)} mau can cham ra {args.out}")
        return
    labels = parse_sheet(args.sheet, {s["id"] for s in samples})
    LABELS_DIR.mkdir(exist_ok=True)
    out = LABELS_DIR / f"{args.rater}.json"
    out.write_text(json.dumps(labels, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Da ghi {len(labels)}/{sum(needs_label(s) for s in samples)} nhan vao {out}")


if __name__ == "__main__":
    main()
