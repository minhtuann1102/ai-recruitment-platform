"""T030: review-textbook-score — thoat 1 khong ghi gi khi sai; dat thi decisions khong chua doan moi, approved_by rong."""
import json

import pytest
from textbook_review_fixtures import SOURCE, item_id, make_record, read_review_dir, textbook_env, write_judgments, write_processed  # noqa: F401

from pipeline.__main__ import main
from pipeline.qa_record_builder import content_hash
from pipeline.textbook_review_decisions import Decisions, load_decisions, save_decisions

DECISIONS_FILE = f"{SOURCE}-decisions.json"
TRIM_TEXT = "Edit this page on GitHub"


@pytest.fixture()
def prepared(textbook_env):
    """5 doan that, 2 lo (batch-size 3); tra (env, records)."""
    records = [make_record(n) for n in range(5)]
    records[1] = make_record(1, content=records[1]["content"] + "\n\n" + TRIM_TEXT)  # doan co dong thua can cat
    write_processed(textbook_env, records)
    assert main(["review-textbook-prepare", "--source", SOURCE, "--batch-size", "3"]) == 0
    return textbook_env, records


def score():
    return main(["review-textbook-score", "--source", SOURCE])


def test_pass_writes_decisions_without_canaries_and_empty_approved_by(prepared, capsys):
    env, records = prepared
    write_judgments(env, {
        item_id(records[0]): {"verdict": "drop", "reason": "off_topic", "note": "marketing"},
        item_id(records[1]): {"verdict": "trim", "remove": [TRIM_TEXT]},
    })
    assert score() == 0
    saved = json.loads((env.decisions / DECISIONS_FILE).read_text(encoding="utf-8"))
    assert saved["approved_by"] == "" and saved["source_id"] == SOURCE
    assert not {content_hash(c["content"]) for c in env.canaries} & set(saved["decisions"])
    assert set(saved["decisions"]) == {r["content_hash"] for r in records}  # hash day du, chi doan that
    assert all(len(h) == 32 for h in saved["decisions"])
    assert saved["decisions"][records[0]["content_hash"]] == {"verdict": "drop", "reason": "off_topic", "note": "marketing"}
    assert saved["decisions"][records[1]["content_hash"]] == {"verdict": "trim", "remove": [TRIM_TEXT]}
    out = capsys.readouterr().out
    assert "3 keep, 1 trim, 1 drop (off_topic 1)" in out and records[1]["content_hash"] in out and "Topic 0" in out


def assert_fails_and_writes_nothing(env, capsys, expect):
    assert score() == 1
    assert expect in capsys.readouterr().err
    assert not (env.decisions / DECISIONS_FILE).exists()


def test_canary_judged_keep_fails_and_names_batch(prepared, capsys):
    env, _ = prepared
    _, key = read_review_dir(env)
    write_judgments(env, {key["batch-02"][0]: {"verdict": "keep"}})
    assert_fails_and_writes_nothing(env, capsys, "batch-02")


def test_missing_item_id_fails(prepared, capsys):
    env, records = prepared
    write_judgments(env, {item_id(records[3]): None})
    assert_fails_and_writes_nothing(env, capsys, "thieu 1 item_id")


def append_line(env, text):
    path = env.work / SOURCE / "judgments-01.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + text + "\n", encoding="utf-8")
    return path


def test_extra_or_duplicate_item_id_fails(prepared, capsys):
    env, _ = prepared
    write_judgments(env)
    path = append_line(env, json.dumps({"item_id": "0" * 12, "verdict": "keep"}))
    assert_fails_and_writes_nothing(env, capsys, "thua")
    write_judgments(env)
    append_line(env, path.read_text(encoding="utf-8").splitlines()[0])
    assert_fails_and_writes_nothing(env, capsys, "hai lan")


@pytest.mark.parametrize("remove", [["Not in the passage at all"], ["term0x1"], [""]])
def test_trim_string_not_matching_exactly_once_fails(prepared, capsys, remove):
    env, records = prepared
    write_judgments(env, {item_id(records[0]): {"verdict": "trim", "remove": remove}})
    assert score() == 1
    assert "loi:" in capsys.readouterr().err
    assert not (env.decisions / DECISIONS_FILE).exists()


@pytest.mark.parametrize("judgment", [{"verdict": "maybe"}, {"verdict": "drop"}, {"verdict": "drop", "reason": "boring"}])
def test_bad_verdict_or_drop_reason_fails(prepared, capsys, judgment):
    env, records = prepared
    write_judgments(env, {item_id(records[0]): judgment})
    assert score() == 1
    assert not (env.decisions / DECISIONS_FILE).exists()


def test_missing_judgments_file_or_batches_fails(prepared, capsys):
    env, _ = prepared
    assert_fails_and_writes_nothing(env, capsys, "thieu judgments-01.jsonl")
    write_judgments(env)
    (env.work / SOURCE / "judgments-09.jsonl").write_text("", encoding="utf-8")
    assert_fails_and_writes_nothing(env, capsys, "judgments-09.jsonl")


def test_merge_keeps_old_decisions_and_resets_approval(prepared):
    env, records = prepared
    old = {"verdict": "drop", "reason": "nav"}
    save_decisions(Decisions(source_id=SOURCE, approved_by="DE", decisions={"b" * 32: old}))
    write_judgments(env)
    assert score() == 0
    saved = load_decisions(SOURCE)
    assert saved.approved_by == "" and saved.decisions["b" * 32] == old
    assert set(saved.decisions) == {"b" * 32, *(r["content_hash"] for r in records)}
