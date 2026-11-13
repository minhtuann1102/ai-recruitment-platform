"""Lenh scope-check-prepare (spec 005 FR-030, T067): chuan bi lo cho judge ra soat "dap an co y cau hoi khong hoi" tren
cac nua cau tach doi (B5). Offline, tat dinh, khong goi LLM.

Chon moi cap seed co split_from, doi ra khoa nua `<qa_id goc>/<a|b>` (a, b = vi tri trong qa-split-map.json), bo cac nua da
co trong qa-split-reviewed.json; so luong phai bang --expect (mac dinh 222 = 262 - 40). --ids chon thang cac nua do
(bo qua loc "da duyet" va --expect: de kiem lai nua da sua, hoac hieu chinh tren nua da duyet voi --seeds-dir tro toi
ban seed cu). Moi item mang theo cac y (qa_scope_check_points) cua nua do va nua anh em, cau goc neu co --originals.
Ghi batch-NN.json (mang item, xep theo item_id) + manifest.json {count, batches, item_ids} vao --out-dir.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .qa_scope_check_points import BATCH_GLOB, MANIFEST_NAME, ScopeCheckError, check_fences, segment_answer
from .qa_seed_loader import SeedError, load_seed_items
from .settings import APP_DIR, CURATED_DATASET, SEEDS_DIR, catalog_dir
from .topic_catalog_reader import CatalogError, load_topics

REVIEWS_DIR = APP_DIR / "data" / "reviews"
SPLIT_MAP_PATH = REVIEWS_DIR / "qa-split-map.json"
SPLIT_REVIEWED_PATH = REVIEWS_DIR / "qa-split-reviewed.json"
DEFAULT_EXPECT = 222
DEFAULT_BATCH_SIZE = 28


def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScopeCheckError(f"khong doc duoc {path}: {exc}") from exc


def read_object(path: Path) -> Dict[str, Any]:
    doc = read_json(path)
    if not isinstance(doc, dict):
        raise ScopeCheckError(f"{path}: phai la object JSON")
    return doc


def read_reviewed(path: Path) -> Dict[str, str]:
    """Khoa `<qa_id goc>/<a|b>` -> ket luan cua qa-split-reviewed.json (truong `reviewed`)."""
    doc = read_json(path)
    reviewed = doc.get("reviewed") if isinstance(doc, dict) else None
    if not isinstance(reviewed, dict):
        raise ScopeCheckError(f"{path}: thieu truong 'reviewed' (object)")
    return reviewed


def half_key(pair: Dict, split_map: Dict[str, List[str]]) -> str:
    """`<qa_id goc>/<a|b>` theo vi tri qa_id trong qa-split-map.json (khong suy tu viec qa_id co bang id goc)."""
    original = pair["split_from"]
    halves = split_map.get(original) if isinstance(split_map, dict) else None
    if not isinstance(halves, list) or len(halves) != 2 or len(set(map(str, halves))) != 2:
        raise ScopeCheckError(f"{pair['qa_id']}: split_from={original} khong co trong qa-split-map.json, hoac khong phai "
                              f"danh sach 2 qa_id khac nhau: {halves!r}")
    if pair["qa_id"] not in halves:
        raise ScopeCheckError(f"{pair['qa_id']}: khong nam trong qa-split-map.json[{original}] = {halves}")
    return f"{original}/{'ab'[halves.index(pair['qa_id'])]}"


def _side(pair: Dict) -> Dict[str, Any]:
    return {"question": pair["question"], "points": segment_answer(pair["answer"])}


def build_items(pairs: List[Dict], split_map: Dict[str, List[str]], reviewed: Dict[str, str],
                topics: List[Dict[str, str]], originals: Optional[Dict[str, str]] = None,
                ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Cac item xep theo item_id. Anh em tra tren ca tap nua (ke ca nua da duyet), khong chi tap duoc chon."""
    halves = {p["qa_id"]: p for p in pairs if isinstance(p, dict) and p.get("split_from")}
    for qa_id, pair in halves.items():
        missing = [f for f in ("topic_id", "question", "answer") if not isinstance(pair.get(f), str)]
        if missing:
            raise ScopeCheckError(f"{qa_id}: thieu truong {', '.join(missing)}")
        fence_problem = check_fences(pair["answer"])
        if fence_problem:
            raise ScopeCheckError(f"{qa_id}: dap an co khoi code ``` khong tach y an toan duoc ({fence_problem}); sua seed")
    keys = {qa_id: half_key(pair, split_map) for qa_id, pair in halves.items()}
    unknown = sorted(set(ids or []) - set(halves))
    if unknown:
        raise ScopeCheckError(f"--ids khong phai nua tach doi trong seed: {', '.join(unknown)}")
    chosen = sorted(set(ids)) if ids else sorted(qa for qa, key in keys.items() if key not in reviewed)
    by_topic = {t["id"]: t for t in topics}
    items = []
    for qa_id in chosen:
        pair, key = halves[qa_id], keys[qa_id]
        original = pair["split_from"]
        sibling_id = next(x for x in split_map[original] if x != qa_id)
        if sibling_id not in halves:
            raise ScopeCheckError(f"{qa_id}: khong thay nua anh em {sibling_id} trong seed")
        if pair["topic_id"] not in by_topic:
            raise ScopeCheckError(f"{qa_id}: topic_id {pair['topic_id']} khong co trong catalog")
        topic, sibling = by_topic[pair["topic_id"]], _side(halves[sibling_id])
        items.append({"item_id": qa_id, "half": key, "topic_id": pair["topic_id"], "topic_title": topic["title"],
                      "key_concepts": topic["key_concepts"], **_side(pair),
                      "sibling_question": sibling["question"], "sibling_points": sibling["points"],
                      "original_question": (originals or {}).get(original)})
    return items


def write_batches(items: List[Dict], out_dir: Path, batch_size: int) -> int:
    """batch-NN.json + manifest.json; xoa batch-*.json cu truoc de lan chay nho hon khong de lai lo thua."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob(BATCH_GLOB):
        stale.unlink()
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    for number, batch in enumerate(batches, start=1):
        (out_dir / f"batch-{number:02d}.json").write_text(
            json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"count": len(items), "batches": len(batches), "item_ids": [i["item_id"] for i in items]}
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(batches)


def run_scope_check_prepare(args: argparse.Namespace) -> int:
    ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()]
    try:
        if args.batch_size < 1:
            raise ScopeCheckError("--batch-size phai >= 1")
        items_in = load_seed_items([(Path(args.seeds_dir), CURATED_DATASET)])
        split_map = read_object(Path(args.split_map))
        reviewed = read_reviewed(Path(args.reviewed))
        originals = read_object(Path(args.originals)) if args.originals else None
        topics = load_topics([Path(args.catalog_dir) if args.catalog_dir else catalog_dir()])
        items = build_items([i.data for i in items_in], split_map, reviewed, topics, originals, ids)
        if not ids and len(items) != args.expect:
            raise ScopeCheckError(f"co {len(items)} nua can ra soat, mong doi {args.expect} (--expect); khong ghi gi. "
                                  f"Kiem tra seed, qa-split-map.json, qa-split-reviewed.json")
    except (ScopeCheckError, SeedError, CatalogError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return 1
    batches = write_batches(items, Path(args.out_dir), args.batch_size)
    print(f"== scope-check-prepare: {len(items)} nua, {batches} lo (<= {args.batch_size}) -> {args.out_dir}")
    return 0


def add_parser(sub) -> None:
    prep = sub.add_parser("scope-check-prepare", help="chuan bi lo judge ra soat y dap an ngoai cau hoi cho nua tach doi")
    prep.add_argument("--out-dir", required=True, metavar="DIR", help="ghi batch-NN.json + manifest.json vao day")
    prep.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="so item moi lo")
    prep.add_argument("--expect", type=int, default=DEFAULT_EXPECT, help="so nua mong doi; lech thi thoat loi, khong ghi")
    prep.add_argument("--originals", metavar="FILE", help="JSON {qa_id goc: cau hoi goc}; khong co thi original_question = null")
    prep.add_argument("--ids", metavar="ID,ID", help="chi cac qa_id nay (bo loc 'da duyet' va --expect)")
    prep.add_argument("--seeds-dir", default=str(SEEDS_DIR), metavar="DIR", help="thu muc seed (vd ban cu de hieu chinh)")
    prep.add_argument("--split-map", default=str(SPLIT_MAP_PATH), metavar="FILE")
    prep.add_argument("--reviewed", default=str(SPLIT_REVIEWED_PATH), metavar="FILE")
    prep.add_argument("--catalog-dir", metavar="DIR", help="thu muc YAML catalog; mac dinh CATALOG_DIR")
