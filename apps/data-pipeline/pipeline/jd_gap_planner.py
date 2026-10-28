"""Ke hoach JD synthetic theo o thieu (spec 009 research R9, FR-022, FR-023; data-model "Gap Cell").

Luoi 5 nhom ky nang x 6 cap bac x 3 thanh pho = 90 o, so JD hien co cua moi o doc tu `cells` cua bao cao process-jd
(crawled + synthetic). Hai buoc, deu cong tung JD mot vao o it JD nhat (hoa -> thu tu co dinh group, level, city):
1. Bu so luong: need_total = max(0, target - jd_out).
2. Bu san da dang, tinh tren so da cong buoc 1: moi nhom ky nang, moi cap Junior / Mid / Senior, moi thanh pho can
   >= floor JD hop le; gia tri nao thieu thi chi cong vao o thuoc gia tri do.
Ham thuan, deterministic: cung bao cao -> cung ke hoach.
"""
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from .jd_normalizer import LEVELS
from .skill_dictionary import GROUPS

CITIES = ("Hà Nội", "Hồ Chí Minh", "Đà Nẵng")
FLOOR_LEVELS = ("Junior", "Mid", "Senior")
DEFAULT_TARGET = 500
DEFAULT_FLOOR = 20

Cell = Tuple[str, str, str]  # (group, level, city)
GRID: Tuple[Cell, ...] = tuple((g, lv, c) for g in GROUPS for lv in LEVELS for c in CITIES)
_GRID_INDEX = {cell: i for i, cell in enumerate(GRID)}
# (vi tri trong Cell, cac gia tri can dat san)
_FLOOR_AXES = ((0, GROUPS), (1, FLOOR_LEVELS), (2, CITIES))
_DISTRIBUTION_FIELDS = ("group", "level", "city")


@dataclass
class GapPlan:
    valid: int  # jd_out cua bao cao
    need_total: int  # phan bu so luong (buoc 1)
    floor_added: int  # phan bu san (buoc 2)
    cells: List[Dict] = field(default_factory=list)  # [{group, level, city, current, add}], add > 0, thu tu GRID

    @property
    def total(self) -> int:
        return self.need_total + self.floor_added


def current_counts(report: Dict) -> Dict[Cell, int]:
    """So JD hop le (crawl + synthetic) cua moi o trong luoi; o ngoai luoi (vd Hai Phong) bo qua."""
    counts = {cell: 0 for cell in GRID}
    for row in report.get("cells") or []:
        cell = (row.get("group"), row.get("level"), row.get("city"))
        if cell in counts:
            counts[cell] += int(row.get("crawled") or 0) + int(row.get("synthetic") or 0)
    return counts


def _axis_totals(report: Dict, counts: Dict[Cell, int]) -> List[Dict[str, int]]:
    """Tong JD hop le theo tung truc (group, level, city): lay distribution cua bao cao (gom ca JD ngoai luoi);
    bao cao khong co distribution -> cong tu cac o."""
    distribution = report.get("distribution") or {}
    totals = []
    for axis, name in enumerate(_DISTRIBUTION_FIELDS):
        if name in distribution:
            totals.append({k: int(v) for k, v in distribution[name].items()})
        else:
            per_value: Dict[str, int] = {}
            for cell, n in counts.items():
                per_value[cell[axis]] = per_value.get(cell[axis], 0) + n
            totals.append(per_value)
    return totals


def _least_filled(candidates: Iterable[Cell], counts: Dict[Cell, int]) -> Cell:
    return min(candidates, key=lambda cell: (counts[cell], _GRID_INDEX[cell]))


def plan_gaps(report: Dict, target: int = DEFAULT_TARGET, floor: int = DEFAULT_FLOOR) -> GapPlan:
    counts = current_counts(report)
    added = {cell: 0 for cell in GRID}
    totals = _axis_totals(report, counts)

    def add_one(cell: Cell) -> None:
        counts[cell] += 1
        added[cell] += 1
        for axis, value in enumerate(cell):
            totals[axis][value] = totals[axis].get(value, 0) + 1

    valid = int(report.get("jd_out") or 0)
    need_total = max(0, target - valid)
    for _ in range(need_total):
        add_one(_least_filled(GRID, counts))

    floor_added = 0
    for axis, values in _FLOOR_AXES:
        for value in values:
            members = [cell for cell in GRID if cell[axis] == value]
            while totals[axis].get(value, 0) < floor:
                add_one(_least_filled(members, counts))
                floor_added += 1

    rows = [
        {"group": g, "level": lv, "city": c, "current": counts[(g, lv, c)] - added[(g, lv, c)], "add": added[(g, lv, c)]}
        for (g, lv, c) in GRID if added[(g, lv, c)]
    ]
    return GapPlan(valid=valid, need_total=need_total, floor_added=floor_added, cells=rows)
