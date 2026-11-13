"""Gop judgments cua nhieu judge thanh bao cao ra soat pham vi (build_report; lenh o qa_scope_check_score). Tat dinh.

- Item that = manifest.json item_ids tru item trong canary-key; item trong lo ma khong thuoc manifest va khong co trong
  canary-key la loi (khong tinh vao so that).
- Co = it nhat mot judge danh dau it nhat mot y sibling / unasked (uu tien recall). `judges` = moi judge xuat hien trong
  cac file judgments. state: judged | unjudged (khong judge nao cham: flagged = None, KHONG phai sach).
  agreement: all = moi judge deu cham va deu co; some = moi judge deu cham, chi mot so co; none = moi judge deu cham, khong ai co;
  partial = co judge chua cham item; None = unjudged.
- missing[judge] = item that judge chua cham hop le; unjudged = item that khong judge nao cham; complete = khong thieu gi
  (ke ca item cai).
- Cau moi (canary-key {item_id: [id y cai]}): judge bat duoc neu danh dau >= 1 y cai; item cai khong tinh vao so that.
- Hieu chinh (truth {item_id: true|false = can sua}): recall / precision cua tung judge va luat hop (union). Item trong
  truth ma mot judge chua cham la loi (khong bo am tham, tranh recall bi thoi phong).
"""
from typing import Any, Dict, List, Set

from .qa_scope_check_judgments import Judgments


def _scored(found: Judgments, judge: str) -> Dict[str, Dict[str, Any]]:
    return found.by_judge.get(judge, {})


def _by_item(real_ids: List[str], found: Judgments, judges: List[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for item_id in real_ids:
        rows = {j: _scored(found, j)[item_id] for j in judges if item_id in _scored(found, j)}
        if not rows:
            out[item_id] = {"state": "unjudged", "flagged": None, "agreement": None, "judges": {}}
            continue
        flagging = [j for j, row in rows.items() if row["flagged_points"]]
        agreement = ("partial" if len(rows) < len(judges) else "none" if not flagging
                     else "all" if len(flagging) == len(rows) else "some")
        out[item_id] = {"state": "judged", "flagged": bool(flagging), "agreement": agreement, "judges": rows}
    return out


def _canaries(items: Dict[str, List[str]], key: Dict[str, Any], found: Judgments, judges: List[str],
              errors: List[str]) -> Dict[str, Any]:
    by_item: Dict[str, Any] = {}
    for item_id, planted in key.items():
        if item_id not in items or not isinstance(planted, list) or not planted or any(
                not isinstance(p, str) or p not in items[item_id] for p in planted):
            errors.append(f"canary-key: {item_id} khong co trong lo hoac id y cai sai: {planted!r}")
            continue
        caught = {j: bool(set(planted) & set(_scored(found, j)[item_id]["flagged_points"]))
                  for j in judges if item_id in _scored(found, j)}
        by_item[item_id] = {"planted": planted, "caught_by": caught}
    per_judge = {j: {"caught": sum(1 for c in by_item.values() if c["caught_by"].get(j)),
                     "judged": sum(1 for c in by_item.values() if j in c["caught_by"])} for j in judges}
    missing = {j: sorted(i for i in by_item if j not in by_item[i]["caught_by"]) for j in judges}
    return {"count": len(by_item), "caught": per_judge, "missing": missing, "by_item": by_item}


def _confusion(pairs: List[tuple]) -> Dict[str, Any]:
    """pairs = [(du doan co, truth can sua)]; recall / precision = None khi mau bang 0."""
    tp = sum(1 for p, t in pairs if p and t)
    fp = sum(1 for p, t in pairs if p and not t)
    fn = sum(1 for p, t in pairs if not p and t)
    return {"items": len(pairs), "tp": tp, "fp": fp, "fn": fn, "tn": len(pairs) - tp - fp - fn,
            "recall": tp / (tp + fn) if tp + fn else None, "precision": tp / (tp + fp) if tp + fp else None}


def _calibration(truth: Dict[str, Any], items: Dict[str, List[str]], real: Set[str], found: Judgments,
                 judges: List[str], errors: List[str]) -> Dict[str, Any]:
    """Item cai trong truth bi bo qua (khong tinh vao so that)."""
    if not truth:
        return {}
    bad = sorted(i for i, v in truth.items() if not isinstance(v, bool))
    if bad:
        errors.append(f"truth: gia tri phai la true/false, sai o: {', '.join(bad)}")
    unknown = sorted(i for i in truth if i not in items)
    if unknown:
        errors.append(f"truth: item_id khong co trong lo: {', '.join(unknown)}")
    usable = {i: v for i, v in truth.items() if i in real and isinstance(v, bool)}
    for judge in judges:
        skipped = sorted(i for i in usable if i not in _scored(found, judge))
        if skipped:
            errors.append(f"truth: judge {judge} chua cham {len(skipped)} item co trong truth: {', '.join(skipped)}")
    per_judge = {j: _confusion([(bool(_scored(found, j)[i]["flagged_points"]), usable[i])
                                for i in usable if i in _scored(found, j)]) for j in judges}
    union = [(any(i in _scored(found, j) and _scored(found, j)[i]["flagged_points"] for j in judges), usable[i])
             for i in usable if any(i in _scored(found, j) for j in judges)]
    return {"truth_items": len(usable), "judges": per_judge, "union": _confusion(union)}


def build_report(items: Dict[str, List[str]], manifest_ids: List[str], found: Judgments, canary_key: Dict[str, Any],
                 truth: Dict[str, Any]) -> Dict[str, Any]:
    """items = {item_id: [id y]} cua moi batch-*.json; manifest_ids = item that do prepare sinh."""
    errors, judges = list(found.errors), sorted(found.judges)
    canaries = _canaries(items, canary_key, found, judges, errors)
    real_ids = sorted(i for i in set(manifest_ids) if i not in canary_key)
    stray = sorted(i for i in items if i not in manifest_ids and i not in canary_key)
    if stray:
        errors.append(f"lo co item khong thuoc manifest va khong co trong canary-key: {', '.join(stray)}")
    absent = sorted(i for i in real_ids if i not in items)
    if absent:
        errors.append(f"manifest co item khong co trong cac file lo: {', '.join(absent)}")
    by_item = _by_item(real_ids, found, judges)
    missing = {j: [i for i in real_ids if i not in _scored(found, j)] for j in judges}
    unjudged = [i for i, v in by_item.items() if v["state"] == "unjudged"]
    return {
        "items": len(real_ids),
        "judges": judges,
        "complete": not unjudged and not any(missing.values()) and not any(canaries["missing"].values()),
        "flagged": sum(1 for v in by_item.values() if v["flagged"]),
        "flagged_all_judges": sum(1 for v in by_item.values() if v["agreement"] == "all"),
        "unjudged": unjudged,
        "by_item": by_item,
        "canaries": canaries,
        "calibration": _calibration(truth, items, set(real_ids), found, judges, errors),
        "errors": errors,
        "missing": missing,
    }
