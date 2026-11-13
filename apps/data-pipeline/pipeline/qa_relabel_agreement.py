"""So nhan cua cac model relabel voi nhan tham chieu (Phase B, spec 005 Session 2026-11-08).

Tham chieu: nhan nguoi cham mu (DE, trang cham 60 cap) hoac ket qua duyet crawl 27/10 (decisions-all.csv).
Chi so (moi chi so tinh tren cac cap ca hai ben deu co nhan):
- fit3: trung topic_fit 3 muc (main | related | off).
- keep: trung quyet dinh giu topic (main) hay khong (related/off) — cai quyet dinh cap co bi doi topic / bo.
- move_topic: trong cac cap nguoi noi khong phai main, model chon cung best_topic_id (ke ca "none").
- difficulty, interview_style: trung tuyet doi.
Dong "enrich (goc)" la nhan DeepSeek luc enrich: topic luon coi la main, do kho la difficulty_before.
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .qa_relabel_command import read_cache
from .settings import PROCESSED_DIR, RELABEL_DIR

METRICS = ("fit3", "keep", "move_topic", "difficulty", "interview_style")
REVIEW_CSV = PROCESSED_DIR / "crawl-review" / "decisions-all.csv"


def _rate(pairs: Iterable[Tuple[object, object]]) -> Tuple[int, int]:
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(1 for a, b in pairs if a == b), len(pairs)


def agreement(model: Dict[str, Dict], reference: Dict[str, Dict]) -> Dict[str, Tuple[int, int]]:
    """{metric: (so cap trung, so cap so duoc)} giua nhan model va nhan tham chieu theo qa_id."""
    common = [qa for qa in reference if qa in model]
    out: Dict[str, Tuple[int, int]] = {}
    out["fit3"] = _rate((model[q].get("topic_fit"), reference[q].get("topic_fit")) for q in common)
    out["keep"] = _rate(
        (None if model[q].get("topic_fit") is None else model[q]["topic_fit"] == "main",
         None if reference[q].get("topic_fit") is None else reference[q]["topic_fit"] == "main") for q in common)
    moved = [q for q in common if reference[q].get("topic_fit") in ("related", "off") and reference[q].get("best_topic_id")]
    out["move_topic"] = _rate((model[q].get("best_topic_id"), reference[q]["best_topic_id"]) for q in moved)
    out["difficulty"] = _rate((model[q].get("difficulty"), reference[q].get("difficulty")) for q in common)
    out["interview_style"] = _rate((model[q].get("interview_style"), reference[q].get("interview_style")) for q in common)
    return out


def baseline_from(judgments: Dict[str, Dict]) -> Dict[str, Dict]:
    """Nhan goc luc enrich, lay tu topic_before / difficulty_before cua mot file judgments bat ky."""
    return {qa: {"topic_fit": "main", "best_topic_id": row["topic_before"], "difficulty": row["difficulty_before"]}
            for qa, row in judgments.items()}


def review_reference(csv_path: Path) -> Dict[str, Dict]:
    """Nhan tu duyet crawl 27/10: chi do kho de xuat va co topic_sai (khong co topic dung co cau truc).
    topic_sai=1 duoc coi la 'khong main' -> chi dung cho chi so keep va difficulty."""
    ref: Dict[str, Dict] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            ref[row["qa_id"]] = {"topic_fit": None, "keep_only": row.get("topic_sai") != "1",
                                 "difficulty": row.get("do_kho_de_xuat") or None}
    return ref


def keep_vs_review(model: Dict[str, Dict], reference: Dict[str, Dict]) -> Tuple[int, int]:
    """Chi so keep voi tham chieu chi co co topic_sai (duyet 27/10)."""
    return _rate((model[q]["topic_fit"] == "main", reference[q]["keep_only"]) for q in reference if q in model)


def format_table(rows: List[Tuple[str, Dict[str, Tuple[int, int]]]], title: str) -> str:
    def cell(v: Optional[Tuple[int, int]]) -> str:
        return "-" if not v or not v[1] else f"{v[0] / v[1]:.0%} ({v[0]}/{v[1]})"
    lines = [f"== {title}", f"{'nguon nhan':<44}" + "".join(f"{m:>18}" for m in METRICS)]
    lines += [f"{name[:44]:<44}" + "".join(f"{cell(stats.get(m)):>18}" for m in METRICS) for name, stats in rows]
    return "\n".join(lines)


def read_human(path: Path) -> Dict[str, Dict]:
    """Nhan nguoi: thu muc <qa_id>.json (xuat tu db trang cham) hoac mot file JSON {qa_id: nhan}."""
    def body(doc: Dict) -> Dict:
        return doc["data"] if isinstance(doc.get("data"), dict) else doc
    if path.is_dir():
        return {f.stem: body(json.loads(f.read_text(encoding="utf-8-sig"))) for f in sorted(path.glob("*.json"))}
    return {qa: body(doc) for qa, doc in json.loads(path.read_text(encoding="utf-8-sig")).items()}


def run_relabel_score(args: argparse.Namespace) -> int:
    files = [Path(f) for f in args.judgments] or sorted(RELABEL_DIR.glob("judgments-*.jsonl"))
    if not files:
        print(f"loi: khong co file judgments trong {RELABEL_DIR}", file=sys.stderr)
        return 1
    models = {f.stem.removeprefix("judgments-"): read_cache(f) for f in files}
    merged = {qa: row for rows in models.values() for qa, row in rows.items()}
    base = baseline_from(merged)
    if args.human:
        human = {qa: r for qa, r in read_human(Path(args.human)).items() if r.get("topic_fit")}
        rows = [(name, agreement(rows, human)) for name, rows in models.items()]
        rows.append(("enrich (goc, DeepSeek)", agreement(base, human)))
        print(format_table(rows, f"so voi nhan nguoi ({len(human)} cap)"))
    review_csv = Path(args.review_csv)
    if review_csv.exists():
        ref = review_reference(review_csv)
        print(f"== so voi duyet crawl 27/10 ({len(ref)} cap; tham chieu do Claude duyet, thien ve model Claude)")
        for name, rows in [*models.items(), ("enrich (goc, DeepSeek)", base)]:
            keep = keep_vs_review(rows, ref)
            diff = agreement(rows, ref)["difficulty"]
            if keep[1]:
                print(f"  {name[:44]:<44} keep {keep[0] / keep[1]:.0%} ({keep[0]}/{keep[1]})  "
                      f"difficulty {diff[0] / max(diff[1], 1):.0%} ({diff[0]}/{diff[1]})")
    return 0
