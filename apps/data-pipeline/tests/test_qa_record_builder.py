import argparse
import json
import unicodedata

from pipeline import offline_commands
from pipeline.qa_record_builder import build_records, content_hash
from pipeline.qa_seed_loader import SeedItem


def items(*pairs):
    return [SeedItem(data=p, file="seed.json", index=i) for i, p in enumerate(pairs)]


def test_each_pair_yields_question_and_qa_pair(make_pair, topics):
    records, dropped = build_records(items(make_pair(2), make_pair(1)), topics)
    assert dropped == 0
    assert [(r["metadata"]["qa_id"], r["metadata"]["chunk_type"]) for r in records] == [
        ("de-qa-0001", "qa_pair"),
        ("de-qa-0001", "question"),
        ("de-qa-0002", "qa_pair"),
        ("de-qa-0002", "question"),
    ]
    qa_pair, question = records[0], records[1]
    assert question["content"] == make_pair(1)["question"]
    assert qa_pair["content"] == f"{make_pair(1)['question']}\n\n{make_pair(1)['answer']}"
    assert question["category"] == "Backend" and question["source_type"] == "interview_qa"
    assert set(question["metadata"]) == {"qa_id", "chunk_type", "dataset", "tags", "source_url", "license", "synthetic"}


def test_self_source_has_null_source_url(make_pair, topics):
    pair = make_pair(1, source="self", license="CC-BY-4.0", synthetic=True, reviewed_by="DE", attribution=...)
    records, _ = build_records(items(pair), topics)
    assert all(r["metadata"]["source_url"] is None for r in records)


def test_cleans_content_and_keeps_diacritics(make_pair, topics):
    pair = make_pair(1, question="<p>Event  loop\x00 là   gì?</p>")
    records, _ = build_records(items(pair), topics)
    assert records[1]["content"] == "Event loop là gì?"


def test_nfd_and_nfc_give_same_hash(make_pair, topics):
    nfc = make_pair(1, question="Thuật toán băm là gì vậy?")
    nfd = make_pair(1, question=unicodedata.normalize("NFD", "Thuật toán băm là gì vậy?"))
    assert build_records(items(nfc), topics)[0][1]["content_hash"] == build_records(items(nfd), topics)[0][1]["content_hash"]
    assert content_hash("  ABC ") == content_hash("abc")


def test_identical_content_is_deduplicated(make_pair, topics):
    a, b = make_pair(1), make_pair(2)
    b["question"], b["answer"] = a["question"], a["answer"]  # validator chan truoc; builder van dedup
    records, dropped = build_records(items(a, b), topics)
    assert dropped == 2 and len(records) == 2


def test_process_skips_bad_pairs_and_output_is_deterministic(tmp_path, monkeypatch, make_pair, sample_catalog_dir):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    pairs = [make_pair(1), make_pair(2, topic_id="smp.gone.topic"), make_pair(3, topic_id="smp.data.sql-index")]
    (seeds / "seed.json").write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(offline_commands, "SEEDS_DIR", seeds)
    monkeypatch.setattr(offline_commands, "catalog_dir", lambda: sample_catalog_dir)
    args = argparse.Namespace(command="process", extra_catalog=[])

    records, report = offline_commands.process_seed(args)
    assert report.records_in == 3 and report.chunks_out == 4
    assert [r["qa_id"] for r in report.records_rejected] == ["de-qa-0002"]

    first = offline_commands.write_processed(records, tmp_path / "out1").read_bytes()
    second = offline_commands.write_processed(offline_commands.process_seed(args)[0], tmp_path / "out2").read_bytes()
    assert first == second
