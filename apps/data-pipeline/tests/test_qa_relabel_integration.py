"""Phase B noi vao luong load (review 2026-11-08: H1, H2, M1, M5, M6, M7): cham truoc dedup, ap khi load, file hong."""
import argparse
import json

import pytest

import pipeline.offline_commands as offline
import pipeline.qa_relabel_command as command
from pipeline.qa_relabel_apply_command import usable_judgments
from pipeline.qa_relabel_decisions import load_decisions
from pipeline.qa_relabel_prompt import PROMPT_VERSION, parse_judgment
from pipeline.qa_seed_loader import SeedError
from pipeline.settings import RelabelSettings

CR_A, CR_B = "cr-devi-node-0a1b2c3d", "cr-devi-node-0a1b2c3e"


@pytest.fixture()
def data_dirs(tmp_path, monkeypatch, make_pair, sample_catalog_dir):
    """Seed curated 1 cap + crawl 2 cap trung cau hoi (CR_B thua dedup truoc khi ap quyet dinh)."""
    seeds, enriched = tmp_path / "seeds", tmp_path / "enriched"
    seeds.mkdir(), enriched.mkdir()
    (seeds / "a.json").write_text(json.dumps([make_pair(1)], ensure_ascii=False), encoding="utf-8")
    crawled = [make_pair(2, qa_id=qa, question="Promise.all khác Promise.allSettled thế nào khi một promise lỗi?",
                         license="unknown", reviewed_by=...) for qa in (CR_A, CR_B)]
    (enriched / "src.json").write_text(json.dumps(crawled, ensure_ascii=False), encoding="utf-8")
    for module in (offline, command):
        monkeypatch.setattr(module, "catalog_dir", lambda: sample_catalog_dir)
    monkeypatch.setattr(offline, "SEEDS_DIR", seeds)
    monkeypatch.setattr(offline, "ENRICHED_DIR", enriched)
    return enriched


def test_relabel_judges_duplicates_before_dedup(data_dirs):
    pairs, topics = command.crawled_pairs([], enriched_dir=data_dirs)
    assert sorted(p["qa_id"] for p in pairs) == [CR_A, CR_B] and len(topics) == 2


def test_load_applies_decisions_and_reports_drops(data_dirs, monkeypatch, capsys):
    decisions = {CR_A: {"drop": "gpt-6-luna: khong thuoc topic nao"}, CR_B: {"difficulty": "hard"}}
    monkeypatch.setattr(offline, "load_decisions", lambda: ({"model": "gpt-6-luna", "judged": 2}, decisions))
    _, result = offline._load_inputs(argparse.Namespace(extra_catalog=[]), strict=False, near_duplicates=False)
    valid = {i.qa_id: i.data for i in result.valid}
    assert CR_A not in valid and valid[CR_B]["difficulty"] == "hard"  # cap trung con lai co nhan moi
    assert valid[CR_B]["difficulty_enriched"] == "medium"
    assert {"qa_id": CR_A, "reasons": ["relabel: gpt-6-luna: khong thuoc topic nao"]} in offline.rejected_entries(result)
    assert result.report["pairs_in"] == 3  # M6: tinh ca cap bi bo
    assert "ap quyet dinh Phase B: 2 cap, model gpt-6-luna" in capsys.readouterr().out
    _, raw = offline._load_inputs(argparse.Namespace(extra_catalog=[]), strict=False, near_duplicates=False,
                                  apply_relabel=False)
    assert CR_A in {i.qa_id for i in raw.valid}  # relabel cham tren nhan goc


def test_missing_decisions_with_crawled_data_warns(data_dirs, monkeypatch, capsys):
    monkeypatch.setattr(offline, "load_decisions", lambda: ({}, {}))
    offline._load_inputs(argparse.Namespace(extra_catalog=[]), strict=False, near_duplicates=False)
    assert "khong co data/raw/relabel/decisions.json" in capsys.readouterr().err


def test_malformed_decisions_file_is_seed_error(tmp_path):
    path = tmp_path / "decisions.json"
    path.write_text("{khong phai json", encoding="utf-8")
    with pytest.raises(SeedError):
        load_decisions(path)
    path.write_text('{"meta": {}, "decisions": []}', encoding="utf-8")
    with pytest.raises(SeedError):
        load_decisions(path)
    assert load_decisions(tmp_path / "khong-co.json") == ({}, {})


def test_non_string_best_topic_is_invalid_not_crash():
    text = json.dumps({"topic_fit": "off", "best_topic_id": ["a"], "difficulty": "easy", "interview_style": True})
    assert parse_judgment(text, "smp.core.event-loop", {"smp.core.event-loop"}) == (None, "unknown_topic")


def test_rerun_with_everything_cached_does_not_crash(tmp_path, monkeypatch, capsys):
    pair = {"qa_id": CR_A, "topic_id": "smp.core.event-loop", "difficulty": "easy", "question": "q", "answer": "a"}
    out = tmp_path / "judgments-m.jsonl"
    out.write_text(json.dumps({"qa_id": CR_A, "prompt_version": PROMPT_VERSION, "topic_before": pair["topic_id"]})
                   + "\n{dong bi cat", encoding="utf-8")
    monkeypatch.setattr(command, "require_relabel_settings", lambda model="": RelabelSettings("k", "u", "m", "", 10))
    monkeypatch.setattr(command, "crawled_pairs", lambda extra: ([pair], [{"id": pair["topic_id"], "title": "t"}]))
    monkeypatch.setattr(command, "cache_path", lambda model: out)
    monkeypatch.setattr(command, "JudgeClient", lambda settings: argparse.Namespace(complete=None))  # khong duoc goi
    args = argparse.Namespace(model="", extra_catalog=[], ids=None, limit=0, workers=1)
    assert command.run_relabel(args) == 0
    assert "'cached': 1" in capsys.readouterr().out


def test_stale_or_broken_judgments_are_not_used():
    pairs = [{"qa_id": CR_A, "topic_id": "t.now"}, {"qa_id": CR_B, "topic_id": "t.now"}]
    good = {"qa_id": CR_A, "prompt_version": PROMPT_VERSION, "topic_before": "t.now", "topic_fit": "main",
            "best_topic_id": "t.now", "difficulty": "hard", "interview_style": True, "model": "m"}
    rows = {CR_A: good, CR_B: {**good, "qa_id": CR_B, "topic_before": "t.old"},
            "cr-devi-node-ffffffff": {**good, "qa_id": "cr-devi-node-ffffffff"}}
    usable, stats = usable_judgments(rows, pairs, {"t.now"})
    assert set(usable) == {CR_A} and stats["judgment_cu"] == 1 and stats["judgment_khong_con_cap"] == 1
    assert stats["cap_crawl_chua_co_nhan"] == 1
    broken = {CR_A: {k: v for k, v in good.items() if k != "difficulty"}}
    assert usable_judgments(broken, pairs[:1], {"t.now"})[1]["judgment_hong:bad_difficulty"] == 1
