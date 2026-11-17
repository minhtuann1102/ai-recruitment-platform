"""review-textbook-score (spec 012 T029, research R9, contract pipeline-cli-textbook): cham ket luan cua worker.

Doc moi `batch-NN.json` + `judgments-NN.jsonl` trong `TEXTBOOK_REVIEW_WORK_DIR/<source_id>/`. Thoat 1 VA KHONG GHI GI khi:
thieu / thua item_id, verdict sai, drop thieu ly do hop le, chuoi `remove` khong khop dung mot lan (cung luat voi
apply_decision), hoac doan moi khong bi `drop` (in ten lo phai soat lai). Dat -> bo doan moi, doi item_id ve hash day du
(tinh lai tu noi dung), merge_decisions (quyet dinh cu thang) + approved_by = CANARY_GATE_APPROVER (thoat 0 = qua cong
doan moi, khong duyet tay) + save_decisions, in so keep / trim / drop theo ly do va danh sach drop + trim de DE doc lai. Offline.
"""
import argparse
import datetime
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from . import settings
from .qa_record_builder import content_hash
from .textbook_command_common import load_checked_manifest, select_sources
from .textbook_review_decisions import (
    CANARY_GATE_APPROVER, Decisions, apply_decision, load_decisions, merge_decisions, save_decisions,
)
from .textbook_review_prepare import CANARY_KEY_FILE, item_id_of

DROP_REASONS = ("nav", "code_only", "off_topic", "not_self_contained", "reference_table", "other")
VERDICTS = ("keep", "drop", "trim")
EXIT_OK, EXIT_INPUT_ERROR = 0, 1


@dataclass
class SourceScore:
    errors: List[str] = field(default_factory=list)
    redo: List[str] = field(default_factory=list)  # ten lo co doan moi khong bi drop
    decisions: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # hash day du -> quyet dinh (chi doan that)
    contents: Dict[str, str] = field(default_factory=dict)  # hash -> noi dung, de in danh sach duyet


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"khong doc duoc {path}: {exc}") from exc


def _decision_of(raw: Any, content: str) -> Dict[str, Any]:
    """Dong judgments -> quyet dinh chuan hoa; sai thi ValueError (khong chua noi dung doan)."""
    verdict = raw.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError(f"verdict {verdict!r} khong hop le (keep / drop / trim)")
    if verdict == "keep":
        return {"verdict": "keep"}
    if verdict == "drop":
        if raw.get("reason") not in DROP_REASONS:
            raise ValueError(f"drop can reason trong {DROP_REASONS}, nhan {raw.get('reason')!r}")
        note = raw.get("note")
        return {"verdict": "drop", "reason": raw["reason"], **({"note": note} if isinstance(note, str) and note else {})}
    remove = raw.get("remove")
    if not isinstance(remove, list) or not remove or not all(isinstance(s, str) and s for s in remove):
        raise ValueError("trim can `remove` la danh sach chuoi khong rong")
    decision = {"verdict": "trim", "remove": remove}
    apply_decision(content, decision)  # ValueError neu chuoi khong khop dung mot lan (too_short_after_trim thi khong loi)
    return decision


def _score_batch(name: str, items: List[Dict], judgments_path: Path, canary_ids: set, out: SourceScore) -> None:
    contents = {i["item_id"]: i["content"] for i in items}
    if not canary_ids or not canary_ids <= set(contents):
        out.errors.append(f"{name}: canary-key.json khong khop lo (can dung {len(canary_ids)} id nam trong lo)")
        return
    if not judgments_path.exists():
        out.errors.append(f"{name}: thieu {judgments_path.name}")
        return
    seen: Dict[str, Dict[str, Any]] = {}
    for number, line in enumerate(judgments_path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{judgments_path.name}:{number}"
        try:
            raw = json.loads(line)
            item_id = raw.get("item_id") if isinstance(raw, dict) else None
            if item_id not in contents:
                raise ValueError(f"item_id {item_id!r} khong co trong lo (thua)")
            if item_id in seen:
                raise ValueError(f"item_id {item_id} xuat hien hai lan (thua)")
            seen[item_id] = _decision_of(raw, contents[item_id])
        except (ValueError, AttributeError) as exc:  # json.JSONDecodeError la ValueError
            out.errors.append(f"{where}: {exc}")
    missing = sorted(set(contents) - set(seen))
    if missing:
        out.errors.append(f"{name}: thieu {len(missing)} item_id, vd {', '.join(missing[:3])}")
    if any(seen.get(c, {}).get("verdict") not in (None, "drop") for c in canary_ids):
        out.redo.append(name)
    for item_id, decision in seen.items():
        if item_id in canary_ids:
            continue
        full = content_hash(contents[item_id])
        if item_id_of(full) != item_id:
            out.errors.append(f"{name}: item_id {item_id} khong khop hash noi dung (lo bi sua?)")
            continue
        out.decisions[full], out.contents[full] = decision, contents[item_id]


def score_source(source_id: str) -> SourceScore:
    work = Path(settings.TEXTBOOK_REVIEW_WORK_DIR) / source_id
    batch_files = sorted(work.glob("batch-*.json"))
    if not batch_files:
        raise ValueError(f"{source_id}: khong co batch-NN.json trong {work} (chay review-textbook-prepare)")
    key = _read_json(work / CANARY_KEY_FILE)
    out = SourceScore()
    names = []
    for path in batch_files:
        name = path.stem
        names.append(name)
        number = name[len("batch-"):]
        _score_batch(name, _read_json(path), work / f"judgments-{number}.jsonl", set(key.get(name, [])), out)
    for path in sorted(work.glob("judgments-*.jsonl")):
        if "batch-" + path.stem[len("judgments-"):] not in names:
            out.errors.append(f"{path.name}: khong co lo tuong ung (thua)")
    return out


def _heading(content: str) -> str:
    return content.split("\n", 1)[0]


def _print_summary(source_id: str, score: SourceScore) -> None:
    verdicts = Counter(d["verdict"] for d in score.decisions.values())
    drops = Counter(d["reason"] for d in score.decisions.values() if d["verdict"] == "drop")
    by_reason = ", ".join(f"{reason} {n}" for reason, n in sorted(drops.items())) or "-"
    print(f"== review-textbook-score {source_id}: {verdicts['keep']} keep, {verdicts['trim']} trim, "
          f"{verdicts['drop']} drop ({by_reason}); approved_by = {CANARY_GATE_APPROVER} (qua cong doan moi)")
    for full, decision in sorted(score.decisions.items(), key=lambda kv: kv[1]["verdict"]):
        if decision["verdict"] == "keep":
            continue
        detail = decision["reason"] if decision["verdict"] == "drop" else "remove " + json.dumps(decision["remove"], ensure_ascii=False)
        print(f"   {decision['verdict']:<5} {full} | {_heading(score.contents[full])} | {detail}")


def run_review_textbook_score(args: argparse.Namespace) -> int:
    check = load_checked_manifest()
    sources = select_sources(check, args.source) if check else None
    if sources is None:
        return EXIT_INPUT_ERROR
    try:
        scores = {source.source_id: score_source(source.source_id) for source in sources}
    except ValueError as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    failed = False
    for source_id, score in scores.items():
        for message in score.errors[:20]:
            print(f"loi: {source_id}: {message}", file=sys.stderr)
        if score.redo:
            print(f"loi: {source_id}: doan moi khong bi drop, soat lai cac lo: {', '.join(score.redo)}", file=sys.stderr)
        failed = failed or bool(score.errors or score.redo)
    if failed:
        print("khong ghi gi (sua judgments roi chay lai)", file=sys.stderr)
        return EXIT_INPUT_ERROR
    reviewed_at = datetime.date.today().isoformat()
    try:
        for source_id, score in scores.items():
            new = Decisions(source_id=source_id, reviewed_at=reviewed_at, decisions=score.decisions)
            merged = merge_decisions(load_decisions(source_id), new)
            merged.approved_by = CANARY_GATE_APPROVER  # den day moi lo da qua cong (moi doan moi bi drop)
            path = save_decisions(merged)
            _print_summary(source_id, score)
            print(f"   -> {path}")
    except ValueError as exc:  # file decisions cu hong
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    return EXIT_OK
