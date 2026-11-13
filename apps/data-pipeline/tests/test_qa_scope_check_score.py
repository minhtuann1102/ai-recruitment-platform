"""scope-check-score (spec 005 FR-030, T067): gop judge, agreement, canary, hieu chinh, thieu / chua cham, manifest."""
import json

import pytest

from pipeline.__main__ import main
from pipeline.qa_scope_check_judgments import load_batch_items, load_manifest_ids, read_judgments
from pipeline.qa_scope_check_report import build_report

REAL = ("i1", "i2", "i3", "i4")  # manifest = item that; c1 la item cai chen vao lo sau prepare
A, S, U = "asked", "sibling", "unasked"
CANARY = {"c1": ["p3"]}


def row(judge, item, statuses, ids=("p1", "p2", "p3")):
    return {"item_id": item, "judge": judge, "points": [{"id": i, "status": s} for i, s in zip(ids, statuses)]}


ROWS = [
    {**row("a", "i1", [A, S, A]), "summary_vi": "lan sang nua kia", "proposed_fix": {"move": "p2"}},
    row("a", "i2", [A, A, A]), row("a", "i3", [U, A, A]), row("a", "c1", [A, A, U]),
    row("b", "i1", [A, A, S]), row("b", "i2", [U, A, A]), row("b", "c1", [A, A, A]),
    row("b", "i3", [A, "meh", A]),  # status sai: bo ca dong, i3 thanh missing cua b; i4 khong ai cham
]
BAD_LINES = [
    "{khong phai json",
    json.dumps(row("b", "zz", [A, A, A])),  # item_id la
    json.dumps(row("b", "i1", [A, A, S])),  # trung (judge, item_id)
    json.dumps(row("b", "i2", [A], ids=("p9",))),  # id y la
    json.dumps(row("b", "i1", [A, A], ids=("p1", "p2"))),  # thieu id y
]


def write_env(tmp_path, rows, extra_lines=(), items=(*REAL, "c1"), manifest=REAL, with_manifest=True):
    batches = tmp_path / "batches"
    batches.mkdir()
    (batches / "batch-01.json").write_text(json.dumps(
        [{"item_id": i, "points": [{"id": p, "text": p} for p in ("p1", "p2", "p3")]} for i in items]), encoding="utf-8")
    if with_manifest:
        (batches / "manifest.json").write_text(json.dumps({"count": len(manifest), "item_ids": list(manifest)}), encoding="utf-8")
    path = tmp_path / "judgments-x.jsonl"
    path.write_text("\n".join([*(json.dumps(r) for r in rows), *extra_lines]), encoding="utf-8")
    return batches, path


def report_of(env, canary=CANARY, truth=None):
    batches, path = env
    items = load_batch_items(batches)
    return build_report(items, load_manifest_ids(batches), read_judgments([path], items), canary, truth or {})


@pytest.fixture()
def score_env(tmp_path):
    return write_env(tmp_path, ROWS, BAD_LINES)


def run_cli(env, tmp_path, *extra):
    batches, path = env
    return main(["scope-check-score", "--batches-dir", str(batches), "--judgments", str(path),
                 "--out", str(tmp_path / "report.json"), *extra])


def test_flags_agreement_states_and_fix_are_carried_per_item(score_env):
    report = report_of(score_env)
    assert (report["items"], report["judges"], report["flagged"], report["flagged_all_judges"]) == (4, ["a", "b"], 3, 1)
    assert {k: v["agreement"] for k, v in report["by_item"].items()} == {
        "i1": "all", "i2": "some", "i3": "partial", "i4": None}  # i3: b chua cham nen khong the 'all'
    assert "c1" not in report["by_item"]  # item cai khong tinh vao so that
    i1 = report["by_item"]["i1"]["judges"]
    assert i1["a"] == {"flagged_points": ["p2"], "summary_vi": "lan sang nua kia", "proposed_fix": {"move": "p2"}}
    assert i1["b"] == {"flagged_points": ["p3"]}
    assert report["calibration"] == {}


def test_unjudged_item_is_listed_and_never_looks_clean(score_env):
    report = report_of(score_env)
    assert report["unjudged"] == ["i4"]
    assert report["by_item"]["i4"] == {"state": "unjudged", "flagged": None, "agreement": None, "judges": {}}
    assert report["missing"] == {"a": ["i4"], "b": ["i3", "i4"]}
    assert report["complete"] is False


def test_agreement_none_when_every_judge_scored_and_nobody_flags(tmp_path):
    rows = [row(j, i, [A, A, A]) for j in "ab" for i in REAL]
    env = write_env(tmp_path, rows, items=REAL)
    report = report_of(env, canary={})
    assert {v["agreement"] for v in report["by_item"].values()} == {"none"} and report["flagged"] == 0
    assert report["complete"] is True and report["unjudged"] == []
    assert run_cli(env, tmp_path) == 0


def test_missing_items_alone_make_exit_code_1_but_report_is_written_first(tmp_path, capsys):
    rows = [row("a", i, [A, A, A]) for i in REAL] + [row("b", i, [A, S, A]) for i in ("i1", "i3", "i4")]  # b bo i2
    env = write_env(tmp_path, rows, items=REAL)
    assert run_cli(env, tmp_path) == 1
    out = capsys.readouterr()
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["errors"] == [] and report["missing"] == {"a": [], "b": ["i2"]} and report["complete"] is False
    assert report["by_item"]["i2"]["agreement"] == "partial" and report["by_item"]["i2"]["flagged"] is False
    assert "day du: KHONG" in out.out and "thieu b: 1 item that" in out.out


def test_every_kind_of_bad_line_is_listed_without_crashing(score_env):
    errors = report_of(score_env)["errors"]
    assert len(errors) == 6
    for needle in ("JSON hong", "item_id la", "bi cham lan nua", "id y la", "thieu id y", "status khong hop le"):
        assert needle in "\n".join(errors)


def test_canaries_caught_or_missed_per_judge(score_env):
    canaries = report_of(score_env)["canaries"]
    assert canaries["count"] == 1 and canaries["missing"] == {"a": [], "b": []}
    assert canaries["caught"] == {"a": {"caught": 1, "judged": 1}, "b": {"caught": 0, "judged": 1}}
    assert canaries["by_item"]["c1"] == {"planted": ["p3"], "caught_by": {"a": True, "b": False}}


def test_calibration_recall_precision_and_truth_item_a_judge_skipped_is_an_error(score_env):
    truth = {"i1": True, "i2": True, "i3": False, "c1": True}  # c1 la canary: bo qua
    report = report_of(score_env, truth=truth)
    cal = report["calibration"]
    a, b, union = cal["judges"]["a"], cal["judges"]["b"], cal["union"]
    assert cal["truth_items"] == 3
    assert (a["tp"], a["fp"], a["fn"], a["recall"], a["precision"]) == (1, 1, 1, 0.5, 0.5)
    assert (b["items"], b["recall"], b["precision"]) == (2, 1.0, 1.0)
    assert (union["tp"], union["fp"], union["fn"], union["recall"]) == (2, 1, 0, 1.0)
    assert union["precision"] == pytest.approx(2 / 3)
    skipped = [e for e in report["errors"] if e.startswith("truth:")]
    assert len(skipped) == 1 and "judge b chua cham 1 item" in skipped[0] and "i3" in skipped[0]  # khong bo am tham


def test_batch_item_outside_manifest_needs_canary_key_else_error(score_env):
    assert not any("manifest" in e for e in report_of(score_env)["errors"])  # c1 co trong canary-key
    report = report_of(score_env, canary={})
    assert report["items"] == 4 and any("khong thuoc manifest" in e and "c1" in e for e in report["errors"])


def test_missing_manifest_or_batches_dir_exits_1(tmp_path):
    env = write_env(tmp_path, ROWS, with_manifest=False)
    assert run_cli(env, tmp_path) == 1
    assert main(["scope-check-score", "--batches-dir", str(tmp_path / "none"), "--judgments", str(env[1]),
                 "--out", str(tmp_path / "r.json")]) == 1


def test_cli_writes_report_prints_summary_and_exits_1_on_errors(score_env, tmp_path, capsys):
    (tmp_path / "canary.json").write_text(json.dumps(CANARY), encoding="utf-8")
    (tmp_path / "truth.json").write_text(json.dumps({"i1": True, "i2": True, "i3": False}), encoding="utf-8")
    assert run_cli(score_env, tmp_path, "--canary-key", str(tmp_path / "canary.json"), "--truth", str(tmp_path / "truth.json")) == 1
    assert "cau moi a: bat 1/1" in capsys.readouterr().out
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["items"] == 4 and len(report["errors"]) == 7 and report["unjudged"] == ["i4"]  # 6 dong sai + truth i3 cua b
