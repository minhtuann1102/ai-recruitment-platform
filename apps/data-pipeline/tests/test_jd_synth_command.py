"""Lenh synth-jd (spec 009 T036, contracts/pipeline-cli-jd.md): bao cao + raw tu soan trong tmp_path, LLM gia, offline."""
import argparse
import json
from datetime import datetime, timezone

import pytest

from jd_fake_llm import FakeLlm
from pipeline import jd_process_command, jd_synth_command
from pipeline.__main__ import HANDLERS, build_parser
from pipeline.jd_gap_planner import GRID
from pipeline.settings import ConfigError, SKILL_DICTIONARY_PATH

REPORT_TS = "20261028T050000Z"
NOW = datetime(2026, 10, 28, 6, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 28, 7, 0, 0, tzinfo=timezone.utc)
FIRST_CELLS = ["syn-backend-Intern-Hà Nội-1", "syn-backend-Intern-Hồ Chí Minh-1"]


@pytest.fixture()
def dirs(tmp_path):
    return tmp_path / "raw" / "jd", tmp_path / "processed"


def _write_report(processed, jd_out, ts=REPORT_TS):
    """Bao cao du san (moi gia tri 100 JD) nhung chi co jd_out JD hop le; cells rong -> o dau luoi it JD nhat."""
    distribution = {
        "group": {g: 100 for g in {c[0] for c in GRID}}, "level": {lv: 100 for lv in {c[1] for c in GRID}},
        "city": {c: 100 for c in {c[2] for c in GRID}},
    }
    processed.mkdir(parents=True, exist_ok=True)
    report = {"jd_out": jd_out, "cells": [], "distribution": distribution}
    (processed / f"jd-report-{ts}.json").write_text(json.dumps(report), encoding="utf-8")


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _args(**overrides):
    values = {"command": "synth-jd", "target": 500, "limit": None, "dry_run": False}
    values.update(overrides)
    return argparse.Namespace(**values)


def _run(dirs, fake, now=NOW, **overrides):
    raw_dir, processed = dirs
    return jd_synth_command.synth_jd(_args(**overrides), lambda: fake, now, raw_dir, processed, SKILL_DICTIONARY_PATH)


def _synthetic_rows(raw_dir):
    files = sorted((raw_dir / "synthetic").glob("*.jsonl"))
    return files, [json.loads(line) for f in files for line in f.read_text(encoding="utf-8").splitlines()]


def test_cli_registers_synth_jd():
    args = build_parser().parse_args(["synth-jd", "--limit", "10", "--dry-run"])
    assert (args.target, args.limit, args.dry_run) == (500, 10, True)
    assert HANDLERS["synth-jd"] is jd_synth_command.run_synth_jd


def test_missing_report_exits_1(dirs):
    fake = FakeLlm()
    assert _run(dirs, fake) == 1 and fake.calls == []


def test_dry_run_makes_no_llm_call_and_needs_no_key(dirs, capsys):
    _write_report(dirs[1], 498)

    def no_key():
        raise AssertionError("dry-run khong duoc doc key")

    assert jd_synth_command.synth_jd(_args(dry_run=True), no_key, NOW, *dirs, SKILL_DICTIONARY_PATH) == 0
    assert "+1" in capsys.readouterr().out
    assert not (dirs[0] / "synthetic").exists()


def test_missing_key_exits_2_before_any_call(dirs, monkeypatch):
    _write_report(dirs[1], 498)
    monkeypatch.setattr(jd_synth_command, "JD_RAW_DIR", dirs[0])
    monkeypatch.setattr(jd_synth_command, "PROCESSED_DIR", dirs[1])
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert jd_synth_command.run_synth_jd(_args()) == 2

    def raise_config():
        raise ConfigError("thieu LLM_API_KEY")

    assert jd_synth_command.synth_jd(_args(), raise_config, NOW, *dirs, SKILL_DICTIONARY_PATH) == 2
    assert not (dirs[0] / "synthetic").exists()


def test_generates_missing_cells_with_sorted_deterministic_output(dirs):
    _write_report(dirs[1], 498)
    fake = FakeLlm()
    assert _run(dirs, fake) == 0
    files, rows = _synthetic_rows(dirs[0])
    assert [f.name for f in files] == ["20261028T060000Z.jsonl"]
    assert [r["source_job_id"] for r in rows] == sorted(FIRST_CELLS) and len(fake.calls) == 2
    assert all(r["synthetic"] is True and r["source"] == "synthetic" and r["url"] is None for r in rows)
    body = files[0].read_bytes()
    assert b"\r\n" not in body
    assert all(list(json.loads(line)) == sorted(json.loads(line)) for line in body.decode("utf-8").splitlines())


def test_limit_caps_generated_jds(dirs):
    _write_report(dirs[1], 498)
    fake = FakeLlm()
    assert _run(dirs, fake, limit=1) == 0
    assert len(_synthetic_rows(dirs[0])[1]) == 1 and len(fake.calls) == 1


def test_no_missing_cell_makes_no_llm_call(dirs):
    _write_report(dirs[1], 600)
    fake = FakeLlm()
    assert _run(dirs, fake) == 0 and fake.calls == []


def test_second_run_without_process_jd_exits_1(dirs):
    _write_report(dirs[1], 498)
    fake = FakeLlm()
    assert _run(dirs, fake) == 0
    calls = len(fake.calls)
    assert _run(dirs, fake, now=LATER) == 1
    assert len(fake.calls) == calls and len(_synthetic_rows(dirs[0])[0]) == 1


def test_rejected_synthetic_gets_new_id_for_same_cell(dirs):
    raw_dir, processed = dirs
    # lan truoc da sinh -1 cho hai o, process-jd (bao cao moi hon) loai ca hai -> o van thieu
    _write_jsonl(raw_dir / "synthetic" / "20261028T040000Z.jsonl", [{"source_job_id": i} for i in FIRST_CELLS])
    _write_report(processed, 498)
    assert _run(dirs, FakeLlm()) == 0
    new_ids = [r["source_job_id"] for r in _synthetic_rows(raw_dir)[1] if r.get("synthetic")]
    assert new_ids == sorted(i[:-1] + "2" for i in FIRST_CELLS)


def test_failed_jds_exit_3_and_write_nothing(dirs):
    _write_report(dirs[1], 498)
    fake = FakeLlm(lambda messages, attempt: "khong phai json")
    assert _run(dirs, fake) == 3
    assert len(fake.calls) == 2 * 3 and not (dirs[0] / "synthetic").exists()


def test_prompt_has_no_crawl_text_and_company_differs(dirs, make_raw_jd):
    raw_dir, processed = dirs
    crawl = make_raw_jd("1001", company="Công ty Phần mềm Sao Mai")
    _write_jsonl(raw_dir / "itviec" / "20261027T030000Z.jsonl", [crawl])
    _write_report(processed, 498)
    fake = FakeLlm()
    assert _run(dirs, fake) == 0
    prompts = "\n".join(m["content"] for call in fake.calls for m in call)
    crawl_lines = [crawl["title"], crawl["company"], *(l for l in crawl["description_text"].split("\n") if len(l) > 15)]
    assert not [line for line in crawl_lines if line in prompts]
    assert all(r["company"] != crawl["company"] for r in _synthetic_rows(raw_dir)[1])


def test_synthetic_goes_through_process_jd_and_is_counted(dirs, make_raw_jd, monkeypatch):
    raw_dir, processed = dirs
    _write_jsonl(raw_dir / "itviec" / "20261027T030000Z.jsonl", [make_raw_jd("1001")])
    _write_report(processed, 498)
    assert _run(dirs, FakeLlm()) == 0
    for name, value in (("JD_RAW_DIR", raw_dir), ("PROCESSED_DIR", processed),
                        ("JD_NORMALIZED_PATH", processed / "jd_normalized.jsonl"),
                        ("JD_CHUNKS_PATH", processed / "jd_chunks.jsonl")):
        monkeypatch.setattr(jd_process_command, name, value)
    assert jd_process_command.run_process_jd(argparse.Namespace(command="process-jd")) == 0
    [new_report] = [p for p in processed.glob("jd-report-*.json") if REPORT_TS not in p.name]
    report = json.loads(new_report.read_text(encoding="utf-8"))
    assert report["records_in"]["synthetic"] == 2
    assert report["crawl_vs_synthetic"]["crawl"] == 1 and report["crawl_vs_synthetic"]["synthetic"] == 2
    normalized = [json.loads(l) for l in (processed / "jd_normalized.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sum(r["synthetic"] for r in normalized) == 2
