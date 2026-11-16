"""review-textbook-prepare (spec 012 T028, research R9, contract pipeline-cli-textbook): chia doan chua soat thanh lo.

Chon ban ghi da xu ly CHUA co quyet dinh (theo hash goc: metadata.original_hash neu da trim, khong thi content_hash),
chia lo `--batch-size`, moi lo chen 3 doan moi (canary) o vi tri xao theo `--seed` (moi lo mot RNG rieng tu seed + so lo,
nen cung seed cho cung lo). Lo chi co `item_id` (12 ky tu dau cua hash) va `content`: khong lo doan nao la moi.
Ghi `TEXTBOOK_REVIEW_WORK_DIR/<source_id>/batch-NN.json` va `canary-key.json` ({"batch-NN": [item_id]}). Offline.
"""
import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from . import settings
from .qa_record_builder import content_hash
from .textbook_command_common import load_checked_manifest, select_sources
from .textbook_processed_jsonl_reader import original_hash, read_processed
from .textbook_review_decisions import Decisions, load_decisions

CANARIES_FILE = "review-canaries.json"
CANARY_KEY_FILE = "canary-key.json"
CANARIES_PER_BATCH = 3
ITEM_ID_LEN = 12
EXIT_OK, EXIT_INPUT_ERROR = 0, 1


def batch_name(number: int) -> str:
    return f"batch-{number:02d}"


def item_id_of(hash_value: str) -> str:
    return hash_value[:ITEM_ID_LEN]


def load_canaries() -> List[Dict]:
    """Doan moi tu seeds (contract §4): mang {content, kind}; it nhat CANARIES_PER_BATCH doan."""
    path = Path(settings.TEXTBOOK_SOURCES_DIR) / CANARIES_FILE
    try:
        canaries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"khong doc duoc {path}: {exc}") from exc
    ok = isinstance(canaries, list) and all(isinstance(c, dict) and c.get("content") for c in canaries)
    if not ok or len(canaries) < CANARIES_PER_BATCH:
        raise ValueError(f"{path}: can mang >= {CANARIES_PER_BATCH} doi tuong {{content, kind}}")
    return canaries


def pending_items(records: List[Dict], decisions: Decisions) -> List[Dict]:
    """[{item_id, content}] cua ban ghi chua co quyet dinh, theo thu tu file, bo trung hash."""
    seen, items = set(), []
    for record in records:
        key = original_hash(record)
        if key in decisions.decisions or key in seen:
            continue
        seen.add(key)
        items.append({"item_id": item_id_of(record["content_hash"]), "content": record["content"]})
    return items


def build_batches(
    items: List[Dict], canaries: List[Dict], batch_size: int, seed: int
) -> Tuple[List[List[Dict]], Dict[str, List[str]]]:
    """(cac lo, canary-key). Doan that giu thu tu; 3 doan moi chen vao 3 vi tri khac nhau theo RNG cua lo."""
    batches: List[List[Dict]] = []
    key: Dict[str, List[str]] = {}
    for number, start in enumerate(range(0, len(items), batch_size), start=1):
        real = items[start:start + batch_size]
        rng = random.Random(f"{seed}:{number}")
        picked = [{"item_id": item_id_of(content_hash(c["content"])), "content": c["content"]}
                  for c in rng.sample(canaries, CANARIES_PER_BATCH)]
        slots = set(rng.sample(range(len(real) + CANARIES_PER_BATCH), CANARIES_PER_BATCH))
        real_iter, canary_iter = iter(real), iter(picked)
        batch = [next(canary_iter) if i in slots else next(real_iter) for i in range(len(real) + CANARIES_PER_BATCH)]
        batches.append(batch)
        key[batch_name(number)] = [c["item_id"] for c in picked]
    return batches, key


def write_batches(out_dir: Path, batches: List[List[Dict]], key: Dict[str, List[str]]) -> None:
    """Xoa batch-*.json cu (lan chay nho hon khong de lai lo thua) roi ghi lo moi + canary-key.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("batch-*.json"):
        stale.unlink()
    for number, batch in enumerate(batches, start=1):
        (out_dir / f"{batch_name(number)}.json").write_text(
            json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out_dir / CANARY_KEY_FILE).write_text(
        json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _prepare_source(source_id: str, canaries: List[Dict], batch_size: int, seed: int) -> int:
    try:
        records = read_processed(source_id)
    except FileNotFoundError:
        print(f"loi: {source_id}: chua co file da xu ly (chay process-textbook --source {source_id})", file=sys.stderr)
        return EXIT_INPUT_ERROR
    items = pending_items(records, load_decisions(source_id))
    if not items:
        print(f"{source_id}: khong co doan can soat (moi doan da co quyet dinh)")
        return EXIT_OK
    batches, key = build_batches(items, canaries, batch_size, seed)
    if any(len({i["item_id"] for i in batch}) != len(batch) for batch in batches):  # moi co the lap giua cac lo
        print(f"loi: {source_id}: item_id (12 ky tu dau cua hash) bi trung trong mot lo", file=sys.stderr)
        return EXIT_INPUT_ERROR
    out_dir = Path(settings.TEXTBOOK_REVIEW_WORK_DIR) / source_id
    write_batches(out_dir, batches, key)
    print(f"== review-textbook-prepare {source_id}: {len(items)} doan, {len(batches)} lo "
          f"(<= {batch_size} doan that + {CANARIES_PER_BATCH} doan moi moi lo) -> {out_dir}")
    if any(out_dir.glob("judgments-*.jsonl")):
        print("   ! judgments-*.jsonl cu con trong thu muc: xoa truoc khi giao worker lo moi", file=sys.stderr)
    return EXIT_OK


def run_review_textbook_prepare(args: argparse.Namespace) -> int:
    if args.batch_size < 1:
        print("loi: --batch-size phai >= 1", file=sys.stderr)
        return EXIT_INPUT_ERROR
    check = load_checked_manifest()
    sources = select_sources(check, args.source) if check else None
    if sources is None:
        return EXIT_INPUT_ERROR
    try:
        canaries = load_canaries()
        return max(_prepare_source(s.source_id, canaries, args.batch_size, args.seed) for s in sources)
    except ValueError as exc:  # canary hong / decisions hong / file xu ly hong
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
