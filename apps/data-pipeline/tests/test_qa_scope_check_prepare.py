"""scope-check-prepare (spec 005 FR-030, T067): chon nua tach doi, anh em, lo, --ids, kiem tra dau vao."""
import json

import pytest

from pipeline.__main__ import main


def pair(qa_id, original, answer="**H**\n- một\n- hai"):
    return {"qa_id": qa_id, "topic_id": "smp.core.event-loop", "question": f"Hỏi {qa_id}?", "answer": answer,
            "difficulty": "hard", "split_from": original}


@pytest.fixture()
def prep_env(tmp_path, sample_catalog_dir):
    """3 cap tach doi (thu tu map khac nhau) + 1 cap thuong; o2/b da duyet. Tra ve (tmp_path, tuy chon duong dan)."""
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    (seeds / "hard-a.json").write_text(json.dumps([
        pair("o1", "o1"), pair("o1b", "o1"), pair("o2x", "o2"), pair("o2", "o2", "chỉ một đoạn"),
        {"qa_id": "plain", "topic_id": "smp.core.event-loop", "question": "q", "answer": "a", "difficulty": "hard"},
    ], ensure_ascii=False), encoding="utf-8")
    (seeds / "hard-b.json").write_text(json.dumps([pair("o3", "o3"), pair("o3b", "o3")]), encoding="utf-8")
    (tmp_path / "map.json").write_text(json.dumps(
        {"o1": ["o1", "o1b"], "o2": ["o2x", "o2"], "o3": ["o3", "o3b"]}), encoding="utf-8")
    (tmp_path / "reviewed.json").write_text(json.dumps({"note": "x", "reviewed": {"o2/b": "ok"}}), encoding="utf-8")
    (tmp_path / "originals.json").write_text(json.dumps({"o1": "Câu gốc o1?"}, ensure_ascii=False), encoding="utf-8")
    options = ["--seeds-dir", str(seeds), "--split-map", str(tmp_path / "map.json"), "--reviewed",
               str(tmp_path / "reviewed.json"), "--catalog-dir", str(sample_catalog_dir)]
    return tmp_path, options


def run_prepare(env, *extra, out="out"):
    tmp, options = env
    return main(["scope-check-prepare", "--out-dir", str(tmp / out), *options, *extra])


def load_batches(out_dir):
    return [item for f in sorted(out_dir.glob("batch-*.json")) for item in json.loads(f.read_text(encoding="utf-8"))]


def test_prepare_selects_split_halves_minus_reviewed_with_sibling_and_original(prep_env):
    tmp, _ = prep_env
    assert run_prepare(prep_env, "--expect", "5", "--originals", str(tmp / "originals.json"), "--batch-size", "2") == 0
    items = load_batches(tmp / "out")
    assert [i["item_id"] for i in items] == ["o1", "o1b", "o2x", "o3", "o3b"]  # o2 (o2/b) da duyet, plain khong tach doi
    assert [i["half"] for i in items] == ["o1/a", "o1/b", "o2/a", "o3/a", "o3/b"]  # a/b theo vi tri trong split map
    o2x = items[2]  # anh em o2 da duyet nhung van phai co mat
    assert o2x["sibling_question"] == "Hỏi o2?" and o2x["sibling_points"] == [{"id": "p1", "text": "chỉ một đoạn"}]
    assert o2x["original_question"] is None and items[0]["original_question"] == "Câu gốc o1?"
    assert items[0]["points"] == [{"id": "p1", "text": "[H] một"}, {"id": "p2", "text": "[H] hai"}]
    assert (items[0]["topic_title"], items[0]["key_concepts"]) == ("Event loop mẫu", "a, b, c")
    manifest = json.loads((tmp / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest == {"count": 5, "batches": 3, "item_ids": ["o1", "o1b", "o2x", "o3", "o3b"]}


def test_prepare_expect_mismatch_exits_nonzero_and_writes_nothing(prep_env, capsys):
    tmp, _ = prep_env
    assert run_prepare(prep_env) != 0  # mac dinh --expect 222
    assert "mong doi 222" in capsys.readouterr().err
    assert not (tmp / "out").exists()


def test_prepare_ids_bypass_reviewed_filter_and_expect_and_unknown_id_fails(prep_env):
    tmp, _ = prep_env
    assert run_prepare(prep_env, "--ids", "o2, o3b") == 0
    assert [i["half"] for i in load_batches(tmp / "out")] == ["o2/b", "o3/b"]
    assert run_prepare(prep_env, "--ids", "plain", out="out2") == 1  # khong phai nua tach doi


def test_prepare_replaces_stale_batches_and_rejects_unmapped_split(prep_env):
    tmp, _ = prep_env
    run_prepare(prep_env, "--expect", "5", "--batch-size", "1")
    assert len(list((tmp / "out").glob("batch-*.json"))) == 5
    run_prepare(prep_env, "--expect", "5", "--batch-size", "10")
    assert len(list((tmp / "out").glob("batch-*.json"))) == 1
    (tmp / "map.json").write_text(json.dumps({"o1": ["o1", "o1b"]}), encoding="utf-8")
    assert run_prepare(prep_env, "--expect", "5", out="out3") == 1


@pytest.mark.parametrize("answer", ["- a\n```py\nx = 1\n- b", "- Ví dụ: ```py\nx\n```\n- b"])
def test_prepare_fails_on_odd_or_mid_line_fences_and_writes_nothing(prep_env, capsys, answer):
    tmp, _ = prep_env
    (tmp / "seeds" / "hard-b.json").write_text(json.dumps(
        [pair("o3", "o3", answer), pair("o3b", "o3")], ensure_ascii=False), encoding="utf-8")
    assert run_prepare(prep_env, "--expect", "5") == 1
    err = capsys.readouterr().err
    assert "o3" in err and "```" in err
    assert not (tmp / "out").exists()


def test_prepare_gives_clear_errors_for_bad_split_map_entry_and_non_object_originals(prep_env, capsys):
    tmp, _ = prep_env
    (tmp / "map.json").write_text(json.dumps({"o1": ["o1", "o1"], "o2": ["o2x", "o2"], "o3": ["o3", "o3b"]}), encoding="utf-8")
    assert run_prepare(prep_env, "--expect", "5") == 1  # truoc day: StopIteration
    assert "khac nhau" in capsys.readouterr().err
    (tmp / "map.json").write_text(json.dumps({"o1": ["o1", "o1b"], "o2": ["o2x", "o2"], "o3": ["o3", "o3b"]}), encoding="utf-8")
    (tmp / "originals.json").write_text(json.dumps(["không phải object"]), encoding="utf-8")
    assert run_prepare(prep_env, "--expect", "5", "--originals", str(tmp / "originals.json")) == 1
    assert "phai la object JSON" in capsys.readouterr().err
