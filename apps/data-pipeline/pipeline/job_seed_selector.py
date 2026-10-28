"""Chon posting seed cho job_db (spec 009 T041, FR-018, FR-022).

Dieu kien (FR-018): tieu de, mo ta (summary + description + responsibilities + benefits), yeu cau, thanh pho, loai
hinh, `level` co trong experience_levels cua job_db va >= 1 ky nang.
Chon `count` posting, ham thuan deterministic (cung JD -> cung ket qua, khong phu thuoc thu tu dau vao):
1. San da dang: moi nhom ky nang, moi cap Junior / Mid / Senior, moi thanh pho Ha Noi / HCM / Da Nang can >= floor
   posting (floor = count // 10: 200 -> 20, bang san cua synth-jd). Lay JD crawl truoc, het crawl moi lay synthetic.
2. Lap cho du `count` bang JD crawl con lai, het crawl moi toi synthetic (synthetic chi lap phan thieu).
Moi lan lay mot JD o (group, level, city) dang it posting nhat (hoa -> crawl truoc, roi jd_id) de posting trai deu.
JD trung khoa posting (cung cong ty theo slug, tieu de, mo ta ghep; khac nhau o `requirements` nen process-jd giu ca
hai) chi giu JD dau tien, de `count` posting chon ra la `count` posting khac nhau trong job_db (khoa FR-020).
Thieu JD dat dieu kien, hoac mot gia tri can phu khong co JD nao -> `errors` (lenh thoat 1). Gia tri co JD nhung duoi
san -> chi `warnings` (FR-022 la SHOULD).
"""
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from .jd_gap_planner import CITIES, FLOOR_LEVELS
from .skill_dictionary import GROUPS

DEFAULT_COUNT = 200
_SLUG_MAX = 50  # email Employer 'seed-' + slug <= 64 ky tu phan truoc '@'
DESCRIPTION_PARTS = ("summary", "description", "responsibilities", "benefits")  # thu tu ghep job_postings.description
FLOOR_AXES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (("group", GROUPS), ("level", FLOOR_LEVELS), ("city", CITIES))


@dataclass
class SeedSelection:
    selected: List[Dict] = field(default_factory=list)  # thu tu chon, crawl dung truoc
    eligible: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def synthetic(self) -> int:
        return sum(1 for jd in self.selected if jd.get("synthetic"))


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def posting_description(jd: Dict) -> str:
    """Mo ta posting = cac muc khong rong cua JD, theo DESCRIPTION_PARTS, cach nhau mot dong trong."""
    sections = jd.get("sections") or {}
    return "\n\n".join(part for part in (_text(sections.get(name)) for name in DESCRIPTION_PARTS) if part)


def company_slug(company: str) -> str:
    """'Công Ty CP Đất Việt' -> 'cong-ty-cp-dat-viet'; khac hoa / thuong van cung slug (cung mot Employer seed)."""
    ascii_text = unicodedata.normalize("NFKD", company.replace("đ", "d").replace("Đ", "D"))
    ascii_text = ascii_text.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:_SLUG_MAX].rstrip("-") or "company"


def posting_key(jd: Dict) -> Tuple[str, str, str]:
    """Khoa idempotent cua posting trong job_db: (Employer theo slug cong ty, tieu de, mo ta ghep)."""
    return company_slug(jd.get("company") or ""), _text(jd.get("title")), posting_description(jd)


def is_eligible(jd: Dict, levels: Iterable[str]) -> bool:
    sections = jd.get("sections") or {}
    return bool(
        _text(jd.get("title")) and posting_description(jd) and _text(sections.get("requirements"))
        and jd.get("city") and jd.get("work_type") and jd.get("level") in set(levels) and jd.get("skills")
    )


def _cell(jd: Dict) -> Tuple:
    return tuple(jd.get(axis) for axis, _ in FLOOR_AXES)


def select_postings(jds: Iterable[Dict], levels: Iterable[str], count: int = DEFAULT_COUNT) -> SeedSelection:
    levels = set(levels)
    candidates = sorted((jd for jd in jds if is_eligible(jd, levels)), key=lambda jd: (bool(jd.get("synthetic")), jd["jd_id"]))
    eligible, keys = [], set()
    for jd in candidates:  # trung khoa posting: giu JD dau theo thu tu sap xep (crawl truoc)
        if posting_key(jd) not in keys:
            keys.add(posting_key(jd))
            eligible.append(jd)
    result = SeedSelection(eligible=len(eligible))
    if len(candidates) > len(eligible):
        result.warnings.append(f"bo {len(candidates) - len(eligible)} JD trung khoa posting (cong ty, tieu de, mo ta)")
    if len(eligible) < count:
        result.errors.append(f"chi co {len(eligible)} JD dat dieu kien seed, can {count}")
    for axis, values in FLOOR_AXES:
        for value in values:
            if not any(jd.get(axis) == value for jd in eligible):
                result.errors.append(f"khong co JD dat dieu kien nao co {axis} = {value}")
    if result.errors:
        return result

    order = {jd["jd_id"]: i for i, jd in enumerate(eligible)}
    taken: set = set()
    per_cell: Counter = Counter()
    per_value: Counter = Counter()

    def take_from(pool: List[Dict]) -> None:
        jd = min(pool, key=lambda item: (per_cell[_cell(item)], order[item["jd_id"]]))
        taken.add(jd["jd_id"])
        result.selected.append(jd)
        per_cell[_cell(jd)] += 1
        for axis, _ in FLOOR_AXES:
            per_value[(axis, jd.get(axis))] += 1

    def remaining(allow_synthetic: bool, axis: str = "", value: str = "") -> List[Dict]:
        return [
            jd for jd in eligible
            if jd["jd_id"] not in taken and (allow_synthetic or not jd.get("synthetic"))
            and (not axis or jd.get(axis) == value)
        ]

    floor = max(1, count // 10)
    for allow_synthetic in (False, True):  # buoc 1: san, crawl truoc
        for axis, values in FLOOR_AXES:
            for value in values:
                while per_value[(axis, value)] < floor and len(result.selected) < count:
                    pool = remaining(allow_synthetic, axis, value)
                    if not pool:
                        break
                    take_from(pool)
    for allow_synthetic in (False, True):  # buoc 2: lap cho du count, crawl truoc
        while len(result.selected) < count:
            pool = remaining(allow_synthetic)
            if not pool:
                break
            take_from(pool)

    for axis, values in FLOOR_AXES:
        for value in values:
            if per_value[(axis, value)] < floor:
                result.warnings.append(f"{axis} = {value}: {per_value[(axis, value)]} posting, duoi san {floor}")
    return result
