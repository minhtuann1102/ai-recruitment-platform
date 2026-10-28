"""Build + dedup tap Normalized JD (spec 009 research R7, FR-013, FR-014).

Trung jd_id (cung tin o hai file raw) hoac trung content_hash (tin dang lai, hai nguon) -> giu ban nhieu truong khac
rong hon, hoa thi uu tien JD crawl roi jd_id nho hon; ban con lai bi loai 'duplicate'. Cung (cong ty, tieu de) nhung
khac hash -> chi canh bao trung gan dung, giu ca hai. Ket qua sap theo jd_id (deterministic).
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Tuple

from .jd_record_builder import REJECT_DUPLICATE, build_record, jd_id_of
from .skill_dictionary import SkillDictionary
from .text_cleaning import normalize_for_compare


@dataclass
class BuildResult:
    records: List[Dict] = field(default_factory=list)
    rejected: List[Dict] = field(default_factory=list)  # [{jd_id, reason}], sap theo (reason, jd_id)
    near_duplicates: List[List[str]] = field(default_factory=list)  # moi nhom: jd_id cung (cong ty, tieu de)


def filled_fields(record: Dict) -> int:
    """So truong khac rong; moi section tinh rieng."""
    filled = sum(1 for value in record.values() if value not in (None, "", [], {}))
    return filled + len(record.get("sections") or {})


def _rank(record: Dict) -> Tuple:
    # sorted() tang dan -> phan tu dau la ban giu: nhieu truong hon, crawl truoc synthetic, jd_id nho hon
    # (content_hash cuoi cung de thu tu toan phan khi cung jd_id)
    return (-filled_fields(record), record["synthetic"], record["jd_id"], record["content_hash"])


def _keep_best(records: Iterable[Dict], key: Callable[[Dict], str]) -> Tuple[List[Dict], List[Dict]]:
    groups: Dict[str, List[Dict]] = {}
    for record in records:
        groups.setdefault(key(record), []).append(record)
    kept, dropped = [], []
    for group in groups.values():
        best, *rest = sorted(group, key=_rank)
        kept.append(best)
        dropped.extend(rest)
    return kept, dropped


def near_duplicate_groups(records: Iterable[Dict]) -> List[List[str]]:
    groups: Dict[Tuple[str, str], List[str]] = {}
    for record in records:
        key = (normalize_for_compare(record["company"]), normalize_for_compare(record["title"]))
        groups.setdefault(key, []).append(record["jd_id"])
    return sorted(sorted(ids) for ids in groups.values() if len(ids) > 1)


def build_records(raws: Iterable[Dict], dictionary: SkillDictionary) -> BuildResult:
    result = BuildResult()
    built: List[Dict] = []
    for raw in raws:
        record, reason = build_record(raw, dictionary)
        if record is None:
            result.rejected.append({"jd_id": jd_id_of(raw), "reason": reason})
        else:
            built.append(record)
    unique_ids, dropped_ids = _keep_best(built, lambda r: r["jd_id"])
    unique, dropped_hash = _keep_best(unique_ids, lambda r: r["content_hash"])
    result.rejected += [{"jd_id": r["jd_id"], "reason": REJECT_DUPLICATE} for r in dropped_ids + dropped_hash]
    result.rejected.sort(key=lambda r: (r["reason"], r["jd_id"]))
    result.records = sorted(unique, key=lambda r: r["jd_id"])
    result.near_duplicates = near_duplicate_groups(result.records)
    return result
