"""Bo cau hoi cua Interviewer cho nguoi cham (context/quality-criteria.md, Q5 trong docs/ai-service/09).

Lay mau phan tang tu file phien gia lap (moi level 15 cau: 6 ask_main, 4 follow_up, 4 hint, 1 wrap_up/clarify) ->
evals/question_golden.jsonl (du lieu gia lap, khong co du lieu ca nhan). Nguoi cham dien phieu CSV (an nguon cau hoi
bank/ai de khong bi moi): level_fit (de/vua/kho), natural (1-5), action_ok (y/n); nhap lai vao evals/question_labels/.
  python -m evals.question_set build --run ../../plans/reports/eval-sim-bank-after2.json
  python -m evals.question_set export --out /tmp/question_sheet_a.csv
  python -m evals.question_set import --rater rater_a /tmp/question_sheet_a.csv
"""
import argparse
import csv
import json
import random
from pathlib import Path
from typing import Dict, List

from evals.label_sheet import blind_id
from evals.personas import all_personas

GOLDEN = Path(__file__).with_name("question_golden.jsonl")
LABELS_DIR = Path(__file__).with_name("question_labels")
QUOTA = {"ask_main": 6, "follow_up": 4, "hint": 4, "other": 1}  # moi level; other = wrap_up | clarify
LEVEL_FIT = {"de": "too_easy", "vua": "ok", "kho": "too_hard"}
SHEET_FIELDS = ["id", "level", "phase", "action", "difficulty", "topic", "prev_question", "prev_answer", "question",
                "level_fit", "natural", "action_ok", "note"]


def items_from_sessions(sessions: Dict[str, Dict], skip_adversarial: bool = True) -> List[dict]:
    """Moi luot hoi -> mot muc kem ngu canh nguoi cham / judge can (topic, cau truoc va tra loi truoc)."""
    personas, out = all_personas(), []
    for pid, s in sessions.items():
        p = personas.get(pid)
        if p is None or (skip_adversarial and p.behaviors):
            continue
        topics = {t["id"]: t for ph in s["plan"]["phases"] for t in ph["topics"]}
        prev = None
        for t in s["turns"]:
            topic = topics.get(t["topic_id"]) or {}
            out.append({"id": f"{pid}#{t['turn_number']}", "track": p.track, "level": p.level, "phase": t["phase"],
                        "action": t["action"], "difficulty": t["difficulty"], "topic": topic.get("title", ""),
                        "key_points": topic.get("key_points", []), "question": t["question"],
                        "question_source": t.get("question_source"),
                        "prev_question": prev["question"] if prev and t["action"] != "ask_main" else "",
                        "prev_answer": prev["answer"] if prev and t["action"] != "ask_main" else ""})
            prev = t
    return out


def stratified(items: List[dict], seed: int = 7) -> List[dict]:
    rng, out = random.Random(seed), []
    for level in ("fresher", "junior", "middle", "senior"):
        for group, n in QUOTA.items():
            pool = [i for i in items if i["level"] == level and
                    (i["action"] == group or (group == "other" and i["action"] in ("wrap_up", "clarify")))]
            out += rng.sample(pool, min(n, len(pool)))
    return out


def load(path: Path = GOLDEN) -> List[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def export_sheet(items: List[dict], out: Path, seed: int = 11) -> None:
    rows = list(items)
    random.Random(seed).shuffle(rows)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        w.writeheader()
        for i in rows:
            w.writerow({k: i.get(k, "") for k in SHEET_FIELDS[:-4]} | {"id": blind_id(i["id"])})


def parse_sheet(path: Path, known_ids: set) -> Dict[str, dict]:
    """CSV da dien -> {id that: {level_fit, natural, action_ok}}; dong trong bo qua; gia tri sai thi bao loi."""
    real, labels, errors = {blind_id(i): i for i in known_ids}, {}, []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            fit, nat, ok = (row.get(k, "").strip().lower() for k in ("level_fit", "natural", "action_ok"))
            if not (fit or nat or ok):
                continue
            sid = real.get(row["id"].strip())
            if sid is None:
                errors.append(f"{row['id']}: id khong co trong bo cau hoi")
            elif sid in labels:
                errors.append(f"{row['id']}: id bi trung")
            elif fit not in LEVEL_FIT or nat not in {"1", "2", "3", "4", "5"} or ok not in ("y", "n"):
                errors.append(f"{row['id']}: level_fit de|vua|kho, natural 1-5, action_ok y|n")
            else:
                labels[sid] = {"level_fit": LEVEL_FIT[fit], "natural": int(nat), "action_ok": ok == "y"}
    if errors:
        raise ValueError("Phieu sai:\n" + "\n".join(errors))
    return labels


def load_labels(directory: Path = LABELS_DIR) -> Dict[str, Dict[str, dict]]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--run", type=Path, required=True)
    e = sub.add_parser("export")
    e.add_argument("--out", type=Path, required=True)
    i = sub.add_parser("import")
    i.add_argument("--rater", required=True)
    i.add_argument("sheet", type=Path)
    args = parser.parse_args()
    if args.cmd == "build":
        items = stratified(items_from_sessions(json.loads(args.run.read_text(encoding="utf-8"))["sessions"]))
        GOLDEN.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items), encoding="utf-8")
        print(f"Da ghi {len(items)} cau vao {GOLDEN}")
    elif args.cmd == "export":
        export_sheet(load(), args.out)
        print(f"Da ghi phieu {args.out}")
    else:
        labels = parse_sheet(args.sheet, {x["id"] for x in load()})
        LABELS_DIR.mkdir(exist_ok=True)
        (LABELS_DIR / f"{args.rater}.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1), "utf-8")
        print(f"Da nhap {len(labels)} nhan cua {args.rater}")


if __name__ == "__main__":
    main()
