"""T030: review-textbook-prepare — lo co dung 3 doan moi, cung seed cung lo, doan da co quyet dinh khong vao lo, lo khong lo moi."""
import json

from textbook_review_fixtures import SOURCE, item_id, make_record, read_review_dir, textbook_env, write_processed  # noqa: F401

from pipeline.__main__ import main
from pipeline.qa_record_builder import content_hash
from pipeline.textbook_review_decisions import Decisions, save_decisions

PREPARE = ["review-textbook-prepare", "--source", SOURCE]


def run_prepare(*extra):
    return main([*PREPARE, *extra])


def test_every_batch_has_exactly_three_canaries_and_all_real_items_once(textbook_env):
    records = [make_record(n) for n in range(7)]
    write_processed(textbook_env, records)
    assert run_prepare("--batch-size", "3") == 0
    batches, key = read_review_dir(textbook_env)
    assert list(batches) == ["batch-01", "batch-02", "batch-03"]
    canary_hashes = {content_hash(c["content"])[:12] for c in textbook_env.canaries}
    real_ids = [item_id(r) for r in records]
    seen_real = []
    for name, items in batches.items():
        ids = [i["item_id"] for i in items]
        assert len(set(key[name])) == 3 and set(key[name]) <= set(ids) and set(key[name]) <= canary_hashes
        seen_real += [i for i in ids if i not in key[name]]
    assert seen_real == real_ids  # moi doan that dung mot lan, giu thu tu file
    assert [len(items) for items in batches.values()] == [6, 6, 4]  # lo cuoi 1 doan that + 3 doan moi


def test_same_seed_same_batches_and_other_seed_differs(textbook_env):
    write_processed(textbook_env, [make_record(n) for n in range(30)])
    run_prepare("--batch-size", "10", "--seed", "7")
    first = read_review_dir(textbook_env)
    run_prepare("--batch-size", "10", "--seed", "7")
    assert read_review_dir(textbook_env) == first
    run_prepare("--batch-size", "10", "--seed", "8")
    assert read_review_dir(textbook_env) != first


def test_records_with_decisions_are_left_out_including_trimmed_by_original_hash(textbook_env):
    kept, dropped, trimmed, pending = (make_record(n) for n in range(4))
    trimmed["content_hash"] = "f" * 32  # hash SAU trim; khoa quyet dinh la original_hash
    trimmed["metadata"].update(review="trimmed", original_hash="a" * 32)
    write_processed(textbook_env, [kept, dropped, trimmed, pending])
    save_decisions(Decisions(source_id=SOURCE, decisions={
        kept["content_hash"]: {"verdict": "keep"}, dropped["content_hash"]: {"verdict": "drop", "reason": "nav"},
        "a" * 32: {"verdict": "trim", "remove": ["x"]}}))
    assert run_prepare() == 0
    batches, key = read_review_dir(textbook_env)
    real = [i["item_id"] for items in batches.values() for i in items if i["item_id"] not in key["batch-01"]]
    assert real == [item_id(pending)]


def test_batch_exposes_only_item_id_and_content(textbook_env):
    write_processed(textbook_env, [make_record(n) for n in range(4)])
    run_prepare()
    text = (textbook_env.work / SOURCE / "batch-01.json").read_text(encoding="utf-8")
    for entry in json.loads(text):
        assert set(entry) == {"item_id", "content"}
    assert '"kind"' not in text and "canary" not in text.lower()


def test_nothing_pending_prints_message_and_writes_nothing(textbook_env, capsys):
    record = make_record(1)
    write_processed(textbook_env, [record])
    save_decisions(Decisions(source_id=SOURCE, decisions={record["content_hash"]: {"verdict": "keep"}}))
    assert run_prepare() == 0
    assert "khong co doan can soat" in capsys.readouterr().out
    assert not (textbook_env.work / SOURCE).exists()


def test_smaller_rerun_removes_stale_batches(textbook_env):
    write_processed(textbook_env, [make_record(n) for n in range(6)])
    run_prepare("--batch-size", "2")
    assert len(read_review_dir(textbook_env)[0]) == 3
    run_prepare("--batch-size", "6")
    assert list(read_review_dir(textbook_env)[0]) == ["batch-01"]


def test_missing_processed_file_or_unknown_source_exits_one(textbook_env, capsys):
    assert run_prepare() == 1
    assert "chua co file da xu ly" in capsys.readouterr().err
    assert main(["review-textbook-prepare", "--source", "nope"]) == 1
    assert "nope" in capsys.readouterr().err


def test_canary_pool_smaller_than_twelve_exits_one(textbook_env, capsys):
    """L3: contract §4 can >= 12 doan moi (file that co 12); it hon -> xoay vong vo nghia -> tu choi."""
    write_processed(textbook_env, [make_record(n) for n in range(4)])
    (textbook_env.sources / "review-canaries.json").write_text(json.dumps(textbook_env.canaries[:11]), encoding="utf-8")
    assert run_prepare() == 1
    assert ">= 12" in capsys.readouterr().err
    assert not (textbook_env.work / SOURCE).exists()
