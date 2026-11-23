"""T030 (spec 017 US3): schema cvs.json / pool.json / labels.json va so khop tap cap qua loc voi tap cap da gan nhan.

Test dau tien nap ba file seed that da commit (offline): bat loi schema o file that va xac nhan loader nhan cac khoa
phu cua labels.json (rubric, pair_set, agreement, final_source).
"""
import json

import pytest

from pipeline.match_eval_data import (
    EvalDataError, compare_pair_sets, load_cvs, load_eval_data, load_labels, load_pool, require_pair_sets_equal)
from pipeline.settings import MATCH_EVAL_SEEDS_DIR


def profile(name="cv"):
    return {"schema_version": 1, "headline": name, "skills": [{"name": "Java", "category": "language", "evidence": "work"}]}


def cv(cv_id="cv-a", **overrides):
    row = {"cv_id": cv_id, "track": "java_backend", "level": "junior", "note": "ghi chu", "cv_profile": profile(cv_id)}
    row.update(overrides)
    return {k: v for k, v in row.items() if v is not ...}


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def labels_file(labels, **meta):
    doc = {"labeled_by": "llm", "labeled_at": "2026-11-22", "method": "llm+de-blind-20 (final = llm)", "labels": labels}
    doc.update(meta)
    return doc


# ---- seed that ----
def test_committed_seed_files_load_with_extra_label_keys():
    data = load_eval_data(MATCH_EVAL_SEEDS_DIR)
    assert len(data.cvs) == 24 and len(data.jd_ids) == 36 and data.as_of
    assert sum(len(v) for v in data.labels.values()) == 264
    assert {"rubric", "pair_set", "agreement", "final_source"} <= set(data.label_meta)
    assert "labels" not in data.label_meta
    agreement = data.label_meta["agreement"]
    assert agreement["n_blind"] > 0 and 0 < agreement["weighted_kappa_quadratic"] <= 1
    assert set(data.labels) == {c["cv_id"] for c in data.cvs}  # moi CV deu co nhan


# ---- cvs.json ----
def test_cvs_accepts_valid_rows(tmp_path):
    assert [c["cv_id"] for c in load_cvs(write(tmp_path, "cvs.json", [cv("a"), cv("b", level="senior")]))] == ["a", "b"]


@pytest.mark.parametrize("bad, fragment", [
    ([], "rong"),
    ({"cv_id": "a"}, "danh sach"),
    ([cv("a"), cv("a")], "trung cv_id: a"),
    ([cv("a", level="lead")], "level"),
    ([cv("a", track="")], "track"),
    ([cv("a", cv_profile=...)], "cv_profile"),
    ([cv("a", cv_profile=["x"])], "cv_profile"),
    ([cv("a", cv_profile={"headline": "x"})], "skills"),
    ([cv(cv_id=" ")], "cv_id"),
])
def test_cvs_schema_errors(tmp_path, bad, fragment):
    with pytest.raises(EvalDataError) as err:
        load_cvs(write(tmp_path, "cvs.json", bad))
    assert fragment in str(err.value)


def test_missing_or_broken_file_is_a_data_error(tmp_path):
    with pytest.raises(EvalDataError, match="cvs.json"):
        load_cvs(tmp_path / "cvs.json")
    broken = tmp_path / "pool.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(EvalDataError, match="pool.json"):
        load_pool(broken)


# ---- pool.json ----
def test_pool_accepts_valid_file(tmp_path):
    assert load_pool(write(tmp_path, "pool.json", {"as_of": "2026-11-01", "jd_ids": ["x:1", "x:2"]})) == ("2026-11-01", ["x:1", "x:2"])


@pytest.mark.parametrize("bad, fragment", [
    ({"as_of": "01/11/2026", "jd_ids": ["x:1"]}, "as_of"),
    ({"as_of": "2026-13-45", "jd_ids": ["x:1"]}, "as_of"),
    ({"jd_ids": ["x:1"]}, "as_of"),
    ({"as_of": "2026-11-01", "jd_ids": []}, "jd_ids"),
    ({"as_of": "2026-11-01", "jd_ids": ["x:1", "x:1"]}, "trung jd_id: x:1"),
    ({"as_of": "2026-11-01", "jd_ids": ["x:1", 5]}, "jd_ids"),
    ({"as_of": "2026-11-01", "jd_ids": [f"x:{n}" for n in range(201)]}, "200"),
])
def test_pool_schema_errors(tmp_path, bad, fragment):
    with pytest.raises(EvalDataError) as err:
        load_pool(write(tmp_path, "pool.json", bad))
    assert fragment in str(err.value)


# ---- labels.json ----
def test_labels_accept_zero_one_two_and_keep_extra_keys(tmp_path):
    path = write(tmp_path, "labels.json", labels_file({"a": {"x:1": 0, "x:2": 1, "x:3": 2}}, agreement={"n_blind": 3}))
    labels, meta = load_labels(path, {"a"}, {"x:1", "x:2", "x:3"})
    assert labels == {"a": {"x:1": 0, "x:2": 1, "x:3": 2}}
    assert meta["agreement"] == {"n_blind": 3} and meta["labeled_by"] == "llm" and "labels" not in meta


@pytest.mark.parametrize("value", [3, -1, True, False, 1.0, "1", None])
def test_labels_only_accept_integers_zero_one_two(tmp_path, value):
    path = write(tmp_path, "labels.json", labels_file({"a": {"x:1": value}}))
    with pytest.raises(EvalDataError) as err:
        load_labels(path, {"a"}, {"x:1"})
    assert "a" in str(err.value) and "x:1" in str(err.value)


def test_labels_reject_unknown_cv_and_jd_outside_pool(tmp_path):
    with pytest.raises(EvalDataError, match="ghost"):
        load_labels(write(tmp_path, "l1.json", labels_file({"ghost": {"x:1": 1}})), {"a"}, {"x:1"})
    with pytest.raises(EvalDataError, match="x:9"):
        load_labels(write(tmp_path, "l2.json", labels_file({"a": {"x:9": 1}})), {"a"}, {"x:1"})


@pytest.mark.parametrize("meta", [{"labeled_by": ""}, {"method": None}])
def test_labels_require_labeler_and_method(tmp_path, meta):
    doc = labels_file({"a": {"x:1": 1}})
    doc.update(meta)
    with pytest.raises(EvalDataError, match="labeled_by|method"):
        load_labels(write(tmp_path, "labels.json", doc), {"a"}, {"x:1"})


# ---- tap cap qua loc vs tap cap co nhan ----
def test_pair_sets_equal_passes_regardless_of_order():
    check = compare_pair_sets({"a": ["x:2", "x:1"], "b": ["x:1"]}, {"a": {"x:1": 1, "x:2": 0}, "b": {"x:1": 2}})
    assert check.equal and check.missing == [] and check.extra == []
    require_pair_sets_equal(check)


def test_missing_and_extra_pairs_are_listed_sorted():
    check = compare_pair_sets({"a": ["x:1", "x:2", "x:3"], "b": ["x:1"]}, {"a": {"x:1": 1, "x:9": 0}, "c": {"x:1": 1}})
    assert not check.equal
    assert check.missing == [("a", "x:2"), ("a", "x:3"), ("b", "x:1")]  # qua loc nhung chua co nhan
    assert check.extra == [("a", "x:9"), ("c", "x:1")]  # co nhan nhung khong qua loc
    with pytest.raises(EvalDataError) as err:
        require_pair_sets_equal(check)
    text = str(err.value)
    assert "thieu nhan" in text and "a / x:2" in text and "b / x:1" in text
    assert "nhan thua" in text and "a / x:9" in text and "c / x:1" in text


def test_pair_set_report_counts_and_serialises():
    check = compare_pair_sets({"a": ["x:1", "x:2"]}, {"a": {"x:1": 1}})
    as_dict = check.to_dict()
    assert as_dict["equal"] is False and as_dict["filtered_pairs"] == 2 and as_dict["labeled_pairs"] == 1
    assert as_dict["missing"] == [["a", "x:2"]] and as_dict["extra"] == []
