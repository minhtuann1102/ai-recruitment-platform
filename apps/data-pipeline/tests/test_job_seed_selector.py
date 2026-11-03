"""Chon posting seed (spec 009 T042, FR-018, FR-022): JD tu soan, khong I/O."""
from itertools import cycle, islice

from pipeline.jd_gap_planner import CITIES, FLOOR_LEVELS
from pipeline.jd_normalizer import LEVELS
from pipeline.job_seed_selector import is_eligible, posting_description, select_postings
from pipeline.skill_dictionary import GROUPS


def _jd(jd_id, group, level, city, synthetic=False, **overrides):
    jd = {
        "jd_id": jd_id, "title": f"Dev {jd_id}", "city": city, "work_type": "onsite", "level": level,
        "group": group, "skills": ["python"], "synthetic": synthetic,
        "sections": {"summary": "Tom tat", "description": "Mo ta", "requirements": "Yeu cau"},
    }
    jd.update(overrides)
    return jd


def _crawl(n, groups=GROUPS, prefix="c"):
    """n JD crawl rai deu tren cac nhom `groups`, 3 cap san, 3 thanh pho."""
    cells = cycle([(g, lv, c) for g in groups for lv in FLOOR_LEVELS for c in CITIES])
    return [_jd(f"{prefix}{i:03d}", *cell) for i, cell in enumerate(islice(cells, n))]


def _count(selection, axis, value):
    return sum(1 for jd in selection.selected if jd[axis] == value)


def test_enough_crawl_selects_no_synthetic():
    jds = _crawl(300) + [_jd(f"s{i}", "devops", "Mid", "Hà Nội", synthetic=True) for i in range(50)]
    selection = select_postings(jds, LEVELS)
    assert not selection.errors and len(selection.selected) == 200 and selection.synthetic == 0


def test_synthetic_fills_missing_devops_only():
    crawl = _crawl(300, groups=[g for g in GROUPS if g != "devops"])
    synthetic = [_jd(f"s{i:02d}", group, "Mid", "Hà Nội", synthetic=True) for i in range(30) for group in ("devops", "backend")]
    selection = select_postings(crawl + synthetic, LEVELS)
    picked = [jd for jd in selection.selected if jd["synthetic"]]
    assert len(selection.selected) == 200 and len(picked) == 20  # san = 200 // 10
    assert {jd["group"] for jd in picked} == {"devops"}


def test_selection_meets_diversity_floors():
    selection = select_postings(_crawl(400), LEVELS)
    assert not selection.warnings
    for axis, values in (("group", GROUPS), ("level", FLOOR_LEVELS), ("city", CITIES)):
        assert all(_count(selection, axis, value) >= 20 for value in values)


def test_jd_without_allowed_level_is_not_selected():
    jds = _crawl(220) + [_jd("x-nolevel", "backend", None, "Hà Nội"), _jd("x-manager", "backend", "Manager", "Hà Nội")]
    selection = select_postings(jds, ("Intern", "Junior", "Mid", "Senior", "Lead"), count=222)
    assert selection.eligible == 220 and selection.errors == ["chi co 220 JD dat dieu kien seed, can 222"]
    assert not is_eligible(jds[-2], LEVELS) and is_eligible(jds[-1], LEVELS)


def test_missing_required_fields_make_jd_ineligible():
    base = _jd("c1", "backend", "Mid", "Hà Nội")
    assert is_eligible(base, LEVELS)
    for overrides in ({"skills": []}, {"city": None}, {"work_type": None}, {"title": "  "},
                      {"sections": {"summary": "x", "description": "y"}},
                      {"sections": {"requirements": "Yeu cau"}}):
        assert not is_eligible({**base, **overrides}, LEVELS)


def test_value_without_any_jd_is_an_error():
    selection = select_postings(_crawl(300, groups=[g for g in GROUPS if g != "ai_data"]), LEVELS)
    assert selection.selected == [] and selection.errors == ["khong co JD dat dieu kien nao co group = ai_data"]


def test_jd_with_same_posting_key_is_selected_once():
    """Cung cong ty (khac hoa / thuong), tieu de, mo ta; chi khac yeu cau -> mot posting trong job_db."""
    crawl = _crawl(200)
    twin = {**crawl[0], "jd_id": "z-twin", "company": "ACME", "sections": {**crawl[0]["sections"], "requirements": "Khac"}}
    crawl[0]["company"] = "Acme"
    selection = select_postings(crawl + [twin], LEVELS)
    assert selection.eligible == 200 and len(selection.selected) == 200
    assert "z-twin" not in {jd["jd_id"] for jd in selection.selected}
    assert selection.warnings == ["bo 1 JD trung khoa posting (cong ty, tieu de, mo ta)"]


def test_same_input_any_order_same_result():
    jds = _crawl(260) + [_jd(f"s{i}", "frontend", "Senior", "Đà Nẵng", synthetic=True) for i in range(10)]
    first = [jd["jd_id"] for jd in select_postings(jds, LEVELS).selected]
    again = [jd["jd_id"] for jd in select_postings(list(reversed(jds)), LEVELS).selected]
    assert first == again


def test_posting_description_joins_non_empty_parts_in_order():
    jd = _jd("c1", "backend", "Mid", "Hà Nội", sections={
        "benefits": "Luong tot", "summary": " Tom tat ", "description": "", "responsibilities": "Viet API",
        "requirements": "Python",
    })
    assert posting_description(jd) == "Tom tat\n\nViet API\n\nLuong tot"
