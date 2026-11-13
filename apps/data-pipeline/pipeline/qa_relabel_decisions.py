"""Ap ket qua Phase B (spec 005 Session 2026-11-08, FR-028) len cap crawl ma khong sua du lieu goc.

`relabel --apply` gop ba nguon thanh data/raw/relabel/decisions.json:
1. data/reviews/qa-drops.json (commit, chi qa_id + ly do): cap DE quyet bo.
2. Duyet crawl 27/10 (decisions-all.csv): quyet_dinh=drop -> bo; do_kho_de_xuat -> do kho (uu tien hon LLM).
3. judgments-<model>.jsonl cua lenh relabel: topic_fit off/related + best_topic_id khac -> doi topic; off + none ->
   bo (tru cap golden dang dung); do kho + interview_style theo model.
validate / process / index doc file nay va ap khi load dataset de_crawled_qa. data/raw/enriched_qa/ giu nguyen la ban
sao luu: xoa decisions.json la quay ve nhan cu.
"""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .qa_seed_loader import SeedError, SeedItem
from .settings import APP_DIR, CRAWLED_DATASET, GOLDEN_SET_PATH, RELABEL_DIR

DECISIONS_PATH = RELABEL_DIR / "decisions.json"
DROPS_PATH = APP_DIR / "data" / "reviews" / "qa-drops.json"
AIE_EVALS_DIR = APP_DIR.parent / "ai-service" / "evals"
CRAWLED_ID = re.compile(r"cr-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{8}")
DROP_RULE = "relabel"


def golden_qa_ids(paths: Iterable[Path]) -> Set[str]:
    """qa_id cap crawl ma golden set cua DE / AIE dang tro toi: khong duoc bo."""
    found: Set[str] = set()
    for path in paths:
        if path.is_file():
            found |= set(CRAWLED_ID.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return found


def default_golden_files() -> List[Path]:
    return [GOLDEN_SET_PATH, *sorted(AIE_EVALS_DIR.glob("*golden*.json*"))]


def read_review_csv(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["qa_id"]: row for row in csv.DictReader(handle)}


def decide(qa_id: str, judgment: Optional[Dict], review: Optional[Dict[str, str]], de_drop: Optional[str],
           protected: bool) -> Dict:
    """Quyet dinh cho mot cap: {"drop": ly do}, {"golden_kept": ly do bo} (cap golden dang dung: giu nguyen, DE xu ly
    tay), hoac {topic_id?, difficulty?, interview_style?} (chi truong doi)."""
    drop = None
    if de_drop:
        drop = f"DE: {de_drop}"
    elif review and review.get("quyet_dinh") == "drop":
        drop = f"duyet crawl 27/10: {review.get('ly_do', '')[:200]}"
    elif judgment and judgment["topic_fit"] == "off" and judgment["best_topic_id"] == "none":
        drop = f"{judgment['model']}: khong thuoc topic nao trong catalog ({judgment.get('reason', '')[:150]})"
    if drop:
        return {"golden_kept": drop} if protected else {"drop": drop}
    out: Dict = {}
    if judgment:
        fit, best, current = judgment["topic_fit"], judgment["best_topic_id"], judgment["topic_before"]
        if fit != "main" and best not in ("none", current):
            out["topic_id"] = best
        out["difficulty"] = judgment["difficulty"]
        out["interview_style"] = judgment["interview_style"]
    if review and review.get("do_kho_de_xuat"):
        out["difficulty"] = review["do_kho_de_xuat"]
    return out


def build_decisions(judgments: Dict[str, Dict], reviews: Dict[str, Dict[str, str]], de_drops: Dict[str, str],
                    protected: Set[str]) -> Dict[str, Dict]:
    ids = sorted(set(judgments) | set(reviews) | set(de_drops))
    decisions = {qa: decide(qa, judgments.get(qa), reviews.get(qa), de_drops.get(qa), qa in protected) for qa in ids}
    return {qa: d for qa, d in decisions.items() if d}


def write_decisions(decisions: Dict[str, Dict], meta: Dict, path: Path = DECISIONS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"meta": {**meta, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "decisions": decisions}
    path.write_text(json.dumps(body, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return path


def load_decisions(path: Path = DECISIONS_PATH) -> Tuple[Dict, Dict[str, Dict]]:
    """(meta, decisions). Khong co file -> ({}, {}): chua chay relabel-apply, giu nhan enrich. File hong -> SeedError
    (validate / process / index bao loi ro, khong traceback)."""
    if not path.exists():
        return {}, {}
    try:
        body = json.loads(path.read_text(encoding="utf-8-sig"))
        meta, decisions = body.get("meta", {}), body["decisions"]
    except (json.JSONDecodeError, KeyError, AttributeError) as exc:
        raise SeedError(f"{path}: file quyet dinh Phase B hong ({exc}); chay lai relabel-apply hoac xoa file") from exc
    if not isinstance(decisions, dict):
        raise SeedError(f"{path}: 'decisions' phai la object qa_id -> quyet dinh")
    return meta, decisions


def apply_decisions(items: List[SeedItem], decisions: Dict[str, Dict]) -> Tuple[List[SeedItem], List[Tuple[str, str]]]:
    """Chi ap cho dataset de_crawled_qa. Tra (cap giu, [(qa_id, ly do bo)]); nhan goc giu o *_enriched."""
    kept: List[SeedItem] = []
    dropped: List[Tuple[str, str]] = []
    for item in items:
        decision = decisions.get(item.qa_id) if item.dataset == CRAWLED_DATASET and isinstance(item.data, dict) else None
        if not decision:
            kept.append(item)
            continue
        if "drop" in decision:
            dropped.append((item.qa_id, decision["drop"]))
            continue
        if "golden_kept" in decision:  # cap golden: giu nguyen nhan, DE xu ly tay
            kept.append(item)
            continue
        data = dict(item.data)
        for field in ("topic_id", "difficulty"):
            if field in decision and decision[field] != data.get(field):
                data[f"{field}_enriched"] = data.get(field)
                data[field] = decision[field]
        if "interview_style" in decision:
            data["interview_style"] = decision["interview_style"]
        kept.append(SeedItem(data=data, file=item.file, index=item.index, dataset=item.dataset))
    return kept, dropped
