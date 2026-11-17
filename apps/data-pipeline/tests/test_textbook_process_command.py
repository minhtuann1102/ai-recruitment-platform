"""T024: process-textbook qua main(): thu muc du lieu trong tmp_path (monkeypatch settings), file tho fixture."""
import json

from pipeline.__main__ import main
from pipeline.textbook_review_decisions import Decisions, save_decisions
from textbook_command_fixtures import CONSTRAINTS, LOCKING, PROSE, REFERENCE, SOURCE_ID, page, textbook_env  # noqa: F401  (fixture)

RAW_PAGES = [
    page(LOCKING, "Locking", (["Row locks"], PROSE), (["Isolation"], PROSE)),
    page(CONSTRAINTS, "Constraints", (["Unique"], PROSE)),
    # dong manifest cua REFERENCE chi lay sections Cache va Queue
    page(REFERENCE, "Reference", (["Cache"], PROSE), (["Queue"], PROSE), (["Other"], PROSE)),
]


def _lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_raw_file_becomes_processed_file_with_expected_rows(textbook_env, capsys):
    textbook_env.write_raw(RAW_PAGES)
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    rows = _lines(textbook_env.processed_dir / f"{SOURCE_ID}.jsonl")
    assert len(rows) == 5  # 2 + 1 + 2 (section "Other" bi loc theo manifest)
    assert {r["metadata"]["dataset"] for r in rows} == {"de_textbook_valid-source"}
    out = capsys.readouterr().out
    assert "3 trang vao" in out and "5 ban ghi" in out and "chua co quyet dinh soat: 5" in out


def test_running_twice_gives_byte_identical_file_and_empty_source_runs_all_use_sources(textbook_env):
    textbook_env.write_raw(RAW_PAGES)
    out_path = textbook_env.processed_dir / f"{SOURCE_ID}.jsonl"
    assert main(["process-textbook"]) == 0  # bo --source = moi nguon status use
    first = out_path.read_bytes()
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    assert out_path.read_bytes() == first


def test_uses_latest_raw_file_by_name(textbook_env):
    textbook_env.write_raw(RAW_PAGES[:1], name="20261115T080000Z.jsonl")
    textbook_env.write_raw(RAW_PAGES, name="20261116T080000Z.jsonl")
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    assert len(_lines(textbook_env.processed_dir / f"{SOURCE_ID}.jsonl")) == 5


def test_source_without_raw_file_exits_one_and_writes_nothing(textbook_env, capsys):
    assert main(["process-textbook", "--source", SOURCE_ID]) == 1
    assert "chua co file tho" in capsys.readouterr().err
    assert not (textbook_env.processed_dir / f"{SOURCE_ID}.jsonl").exists()


def test_unknown_source_and_broken_manifest_exit_one(textbook_env, capsys):
    textbook_env.write_raw(RAW_PAGES)
    assert main(["process-textbook", "--source", "nope"]) == 1
    (textbook_env.sources_dir / "scenario-queries.yaml").write_text("scn.unknown: {}\n", encoding="utf-8")
    assert main(["process-textbook", "--source", SOURCE_ID]) == 1
    assert "validate-textbook" in capsys.readouterr().err


def test_decisions_are_applied_on_second_run(textbook_env, capsys):
    textbook_env.write_raw(RAW_PAGES)
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    rows = _lines(textbook_env.processed_dir / f"{SOURCE_ID}.jsonl")
    save_decisions(Decisions(SOURCE_ID, "2026-11-16", "tung", {
        rows[0]["content_hash"]: {"verdict": "drop", "reason": "nav"},
        rows[1]["content_hash"]: {"verdict": "keep"},
    }), textbook_env.decisions_dir)
    capsys.readouterr()
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    assert len(_lines(textbook_env.processed_dir / f"{SOURCE_ID}.jsonl")) == 4
    out = capsys.readouterr().out
    assert "review_drop=1" in out and "chua co quyet dinh soat: 3" in out


def test_raw_file_missing_manifest_urls_exits_one_lists_them_and_leaves_processed_file_untouched(textbook_env, capsys):
    """H1: crawl thieu trang -> khong ghi, de index khong xoa doan da nap cua cac trang thieu; file cu giu nguyen."""
    textbook_env.write_raw(RAW_PAGES, name="20261115T080000Z.jsonl")
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    out_path = textbook_env.processed_dir / f"{SOURCE_ID}.jsonl"
    before = out_path.read_bytes()
    textbook_env.write_raw(RAW_PAGES[:1], name="20261116T080000Z.jsonl")  # file moi nhat thieu CONSTRAINTS + REFERENCE
    capsys.readouterr()
    assert main(["process-textbook", "--source", SOURCE_ID]) == 1
    err = capsys.readouterr().err
    assert "thieu 2 URL status use" in err and CONSTRAINTS in err and REFERENCE in err and LOCKING not in err
    assert out_path.read_bytes() == before


def test_missing_urls_for_one_source_does_not_write_it_even_when_nothing_else_is_there(textbook_env):
    textbook_env.write_raw(RAW_PAGES[:2])
    assert main(["process-textbook", "--source", SOURCE_ID]) == 1
    assert not (textbook_env.processed_dir / f"{SOURCE_ID}.jsonl").exists()
