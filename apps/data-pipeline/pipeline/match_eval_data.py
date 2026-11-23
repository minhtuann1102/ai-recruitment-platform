"""Nap + kiem bo du lieu danh gia goi y CV-JD (spec 017 US3, data-model §5): cvs.json, pool.json, labels.json.

Moi loi schema gom lai thanh mot EvalDataError liet ke ro (lenh doi thanh ma thoat 1). labels.json co the co them khoa
phu (rubric, pair_set, agreement, final_source): giu nguyen trong `label_meta`, bao cao in lai cach gan nhan.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .jd_match_index_command import InputError, load_jd_normalized

LEVELS = ("fresher", "junior", "middle", "senior")
LABEL_VALUES = (0, 1, 2)
MAX_JOB_IDS = 200  # tran job_ids cua endpoint (contracts/match-jobs-api.md)
MAX_LISTED = 40  # so dong toi da trong mot thong bao loi
# Ngon ngu JD (009: vi / en / mixed) -> nhom so voi CV tieng Viet (research R9)
LANGUAGE_GROUP = {"vi": "same", "en": "cross", "mixed": "cross"}


class EvalDataError(RuntimeError):
    pass


def _read_json(path: Path):
    if not path.is_file():
        raise EvalDataError(f"chua co {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise EvalDataError(f"{path.name}: JSON loi ({exc})") from exc


def _fail(name: str, problems: Sequence[str]) -> None:
    if problems:
        shown = list(problems[:MAX_LISTED]) + ([f"... va {len(problems) - MAX_LISTED} loi nua"] if len(problems) > MAX_LISTED else [])
        raise EvalDataError(f"{name}: " + "; ".join(shown))


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_cvs(path: Path) -> List[Dict]:
    rows = _read_json(path)
    if not isinstance(rows, list):
        raise EvalDataError(f"{path.name}: phai la danh sach CV")
    if not rows:
        raise EvalDataError(f"{path.name}: danh sach rong")
    problems: List[str] = []
    seen: Set[str] = set()
    for n, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"dong {n}: khong phai object")
            continue
        cv_id = row.get("cv_id")
        label = cv_id if _text(cv_id) else f"dong {n}"
        if not _text(cv_id):
            problems.append(f"{label}: thieu cv_id")
        else:
            if cv_id in seen:
                problems.append(f"trung cv_id: {cv_id}")
            seen.add(cv_id)
        if not _text(row.get("track")):
            problems.append(f"{label}: thieu track")
        if row.get("level") not in LEVELS:
            problems.append(f"{label}: level phai la {'/'.join(LEVELS)} (co {row.get('level')!r})")
        profile = row.get("cv_profile")
        if not isinstance(profile, dict):
            problems.append(f"{label}: cv_profile phai la object")
        elif not isinstance(profile.get("skills"), list):
            problems.append(f"{label}: cv_profile thieu danh sach skills")
    _fail(path.name, problems)
    return rows


def load_pool(path: Path) -> Tuple[str, List[str]]:
    """(as_of, jd_ids)."""
    doc = _read_json(path)
    if not isinstance(doc, dict):
        raise EvalDataError(f"{path.name}: phai la object {{as_of, jd_ids}}")
    problems: List[str] = []
    as_of, ids = doc.get("as_of"), doc.get("jd_ids")
    if not (isinstance(as_of, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of)):
        problems.append(f"as_of phai la YYYY-MM-DD (co {as_of!r})")
    else:
        try:
            date.fromisoformat(as_of)
        except ValueError:
            problems.append(f"as_of khong phai ngay hop le: {as_of}")
    if not isinstance(ids, list) or not ids or not all(_text(j) for j in ids):
        problems.append("jd_ids phai la danh sach khac rong cac ma JD (chuoi)")
    else:
        problems += [f"trung jd_id: {j}" for j in sorted({j for j in ids if ids.count(j) > 1})]
        if len(ids) > MAX_JOB_IDS:
            problems.append(f"jd_ids co {len(ids)} ma, endpoint chi nhan toi da {MAX_JOB_IDS}")
    _fail(path.name, problems)
    return as_of, list(ids)


def load_labels(path: Path, cv_ids: Iterable[str], jd_ids: Iterable[str]) -> Tuple[Dict[str, Dict[str, int]], Dict]:
    """(nhan {cv_id: {jd_id: 0|1|2}}, khoa phu cua labels.json nhu labeled_by / method / agreement)."""
    doc = _read_json(path)
    if not isinstance(doc, dict) or not isinstance(doc.get("labels"), dict):
        raise EvalDataError(f"{path.name}: phai la object co khoa labels = {{cv_id: {{jd_id: nhan}}}}")
    cv_ids, jd_ids = set(cv_ids), set(jd_ids)
    problems = [f"thieu {key}" for key in ("labeled_by", "method") if not _text(doc.get(key))]
    for cv_id, pairs in doc["labels"].items():
        if cv_id not in cv_ids:
            problems.append(f"CV la {cv_id} (khong co trong cvs.json)")
        if not isinstance(pairs, dict):
            problems.append(f"{cv_id}: phai la object {{jd_id: nhan}}")
            continue
        for jd_id, value in pairs.items():
            if jd_id not in jd_ids:
                problems.append(f"{cv_id} / {jd_id}: JD khong co trong pool.json")
            if type(value) is not int or value not in LABEL_VALUES:  # bool va 1.0 deu bi loai
                problems.append(f"{cv_id} / {jd_id}: nhan phai la so nguyen 0, 1 hoac 2 (co {value!r})")
    _fail(path.name, problems)
    return {cv: dict(pairs) for cv, pairs in doc["labels"].items()}, {k: v for k, v in doc.items() if k != "labels"}


@dataclass
class EvalData:
    cvs: List[Dict]
    as_of: str
    jd_ids: List[str]
    labels: Optional[Dict[str, Dict[str, int]]] = None  # None: chua co labels.json (chi cho match-eval-sheet)
    label_meta: Dict = field(default_factory=dict)


def load_eval_data(seeds_dir: Path, require_labels: bool = True) -> EvalData:
    cvs = load_cvs(seeds_dir / "cvs.json")
    as_of, jd_ids = load_pool(seeds_dir / "pool.json")
    labels_path = seeds_dir / "labels.json"
    if not require_labels and not labels_path.is_file():
        return EvalData(cvs, as_of, jd_ids)
    labels, meta = load_labels(labels_path, [c["cv_id"] for c in cvs], jd_ids)
    return EvalData(cvs, as_of, jd_ids, labels, meta)


def load_pool_jds(path: Path, jd_ids: Iterable[str]) -> Dict[str, Dict]:
    """JD chuan hoa (process-jd) cua cac ma trong pool; thieu ma nao -> loi liet ke."""
    try:
        by_id = {jd["jd_id"]: jd for jd in load_jd_normalized(path)}
    except InputError as exc:
        raise EvalDataError(str(exc)) from exc
    missing = [j for j in jd_ids if j not in by_id]
    if missing:
        raise EvalDataError(f"{path.name} thieu {len(missing)} JD cua pool: {', '.join(missing[:MAX_LISTED])}")
    return {j: by_id[j] for j in jd_ids}


def language_groups(jds: Dict[str, Dict]) -> Dict[str, str]:
    """jd_id -> 'same' (JD vi) | 'cross' (en / mixed), so voi CV tieng Viet."""
    unknown = sorted(j for j, jd in jds.items() if jd.get("language") not in LANGUAGE_GROUP)
    if unknown:
        raise EvalDataError(f"JD thieu language vi / en / mixed trong jd_normalized.jsonl: {', '.join(unknown[:MAX_LISTED])}")
    return {j: LANGUAGE_GROUP[jd["language"]] for j, jd in jds.items()}


@dataclass
class PairCheck:
    filtered_pairs: int
    labeled_pairs: int
    missing: List[Tuple[str, str]]  # qua loc cung chua co nhan
    extra: List[Tuple[str, str]]  # co nhan nhung khong qua loc

    @property
    def equal(self) -> bool:
        return not self.missing and not self.extra

    def to_dict(self) -> Dict:
        return {"equal": self.equal, "filtered_pairs": self.filtered_pairs, "labeled_pairs": self.labeled_pairs,
                "missing": [list(p) for p in self.missing], "extra": [list(p) for p in self.extra]}


def compare_pair_sets(filtered: Dict[str, Iterable[str]], labels: Dict[str, Dict[str, int]]) -> PairCheck:
    """So tap cap qua loc cua endpoint voi tap cap da co nhan (T036)."""
    wanted = {(cv, jd) for cv, ids in filtered.items() for jd in ids}
    labeled = {(cv, jd) for cv, pairs in labels.items() for jd in pairs}
    return PairCheck(len(wanted), len(labeled), sorted(wanted - labeled), sorted(labeled - wanted))


def require_pair_sets_equal(check: PairCheck) -> None:
    """Lech thi EvalDataError liet ke tung cap (cv_id / jd_id) de gan bo sung hoac go nhan thua."""
    def lines(pairs: List[Tuple[str, str]]) -> str:
        more = [f"  ... va {len(pairs) - MAX_LISTED} cap nua"] if len(pairs) > MAX_LISTED else []
        return "\n".join([f"  {cv} / {jd}" for cv, jd in pairs[:MAX_LISTED]] + more)

    parts = ([f"thieu nhan cho {len(check.missing)} cap qua loc cung:\n{lines(check.missing)}"] if check.missing else []) + \
            ([f"nhan thua {len(check.extra)} cap khong qua loc:\n{lines(check.extra)}"] if check.extra else [])
    if parts:
        raise EvalDataError("\n".join(parts))
