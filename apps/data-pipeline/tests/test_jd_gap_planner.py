"""Ke hoach o thieu cho synth-jd (spec 009 T031, research R9): bao cao tu soan, khong I/O."""
from pipeline.jd_gap_planner import CITIES, GRID, plan_gaps
from pipeline.jd_normalizer import LEVELS
from pipeline.skill_dictionary import GROUPS


def _report(counts):
    """Bao cao toi gian: cells + distribution + jd_out nhat quan voi counts {(group, level, city): n}."""
    cells = [{"group": g, "level": lv, "city": c, "crawled": n, "synthetic": 0} for (g, lv, c), n in sorted(counts.items())]
    distribution = {"group": {}, "level": {}, "city": {}}
    for (g, lv, c), n in counts.items():
        for name, value in (("group", g), ("level", lv), ("city", c)):
            distribution[name][value] = distribution[name].get(value, 0) + n
    return {"jd_out": sum(counts.values()), "cells": cells, "distribution": distribution}


def test_full_report_gives_empty_plan():
    plan = plan_gaps(_report({cell: 6 for cell in GRID}))  # 540 JD, moi gia tri >= 20
    assert plan.cells == [] and plan.total == 0


def test_missing_ai_data_and_lead_fill_only_those_cells():
    gap = {cell for cell in GRID if cell[0] == "ai_data" or cell[1] == "Lead"}
    counts = {cell: (0 if cell in gap else 8) for cell in GRID}  # 60 o x 8 = 480 JD
    plan = plan_gaps(_report(counts))
    assert plan.need_total == 20
    # sau buoc 1: ai_data co 8 JD (12 o Lead nhom khac dung truoc theo thu tu luoi) -> buoc 2 bu 12 cho ai_data
    assert plan.floor_added == 12 and plan.total == 32
    assert sum(row["add"] for row in plan.cells) == plan.total
    assert all((row["group"], row["level"], row["city"]) in gap for row in plan.cells)
    assert sum(row["add"] for row in plan.cells if row["group"] == "ai_data") == 20
    assert all(row["current"] == 0 for row in plan.cells)


def test_total_never_exceeds_shortfall_when_floors_met():
    counts = {cell: 5 for cell in GRID}  # 450 JD, moi gia tri da >= 20
    plan = plan_gaps(_report(counts), target=460)
    assert plan.total == plan.need_total == 10 and plan.floor_added == 0


def test_floor_counts_jds_outside_grid_from_distribution():
    counts = {cell: 7 for cell in GRID if cell[0] != "devops"}  # 504 JD, devops trong luoi = 0
    report = _report(counts)
    report["distribution"]["group"]["devops"] = 25  # 25 JD devops o thanh pho ngoai luoi (vd Hai Phong)
    report["jd_out"] += 25
    plan = plan_gaps(report)
    assert plan.total == 0


def test_ties_follow_fixed_grid_order_and_are_stable():
    report = _report({cell: 10 for cell in GRID})  # 900 JD, du moi thu
    report["jd_out"] = 497
    first, second = plan_gaps(report), plan_gaps(report)
    assert first.cells == second.cells
    assert [(r["group"], r["level"], r["city"]) for r in first.cells] == [
        (GROUPS[0], LEVELS[0], CITIES[0]), (GROUPS[0], LEVELS[0], CITIES[1]), (GROUPS[0], LEVELS[0], CITIES[2]),
    ]


def test_cells_outside_grid_are_ignored():
    report = _report({cell: 6 for cell in GRID})
    report["cells"].append({"group": "backend", "level": "Mid", "city": "Hải Phòng", "crawled": 50, "synthetic": 0})
    assert plan_gaps(report).total == 0
