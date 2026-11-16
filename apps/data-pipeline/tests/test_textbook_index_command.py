"""T026: check_ready (khong can DB) + index-textbook tu choi offline khi chua duyet / chua soat. Phan DB kiem o quickstart §5."""
import json

from pipeline.__main__ import main
from pipeline.textbook_index_command import check_ready
from pipeline.textbook_review_decisions import Decisions, save_decisions
from textbook_command_fixtures import LOCKING, PROSE, SOURCE_ID, page, textbook_env  # noqa: F401  (fixture)


def _record(h, review=None):
    metadata = {"dataset": "de_textbook_valid-source"}
    if review:
        metadata["review"] = review
    return {"content": f"T > H\n\n{h}", "content_hash": h, "metadata": metadata}


def _approved():
    return Decisions(SOURCE_ID, "2026-11-16", "tung", {})


def test_ready_when_approved_and_every_record_reviewed():
    records = [_record("h1", "keep"), _record("h2", "trimmed")]
    assert check_ready(records, _approved()) == []


def test_empty_approved_by_is_reported():
    problems = check_ready([_record("h1", "keep")], Decisions(SOURCE_ID))
    assert len(problems) == 1 and "approved_by" in problems[0]
    assert len(check_ready([_record("h1", "keep")], Decisions(SOURCE_ID, approved_by="  "))) == 1


def test_unreviewed_record_is_reported_with_count_and_hash():
    problems = check_ready([_record("h1", "keep"), _record("h2"), _record("h3")], _approved())
    assert len(problems) == 1 and "2 doan chua co quyet dinh soat" in problems[0] and "h2" in problems[0]


def test_both_problems_are_listed():
    assert len(check_ready([_record("h1")], Decisions(SOURCE_ID))) == 2


def _process(textbook_env):
    textbook_env.write_raw([page(LOCKING, "Locking", (["Row locks"], PROSE))])
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0


def test_command_refuses_with_exit_one_before_needing_env_or_db(textbook_env, capsys, monkeypatch):
    monkeypatch.delenv("AI_DB_URL", raising=False)
    assert main(["index-textbook", "--source", SOURCE_ID]) == 1  # chua process: khong co file da xu ly
    assert "process-textbook" in capsys.readouterr().err
    _process(textbook_env)
    assert main(["index-textbook", "--source", SOURCE_ID]) == 1  # chua duyet + chua soat, van khong can .env
    err = capsys.readouterr().err
    assert "approved_by" in err and "chua co quyet dinh soat" in err


def test_command_with_approved_decisions_and_reviewed_records_reaches_preflight(textbook_env, capsys, monkeypatch):
    _process(textbook_env)
    path = textbook_env.processed_dir / f"{SOURCE_ID}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    save_decisions(Decisions(SOURCE_ID, "2026-11-16", "tung", {rows[0]["content_hash"]: {"verdict": "keep"}}),
                   textbook_env.decisions_dir)
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    for name in ("EMBEDDING_API_KEY", "LLM_API_KEY", "AI_DB_URL"):
        monkeypatch.delenv(name, raising=False)
    assert main(["index-textbook", "--source", SOURCE_ID]) == 2  # san sang; dung o cau hinh thieu (preflight), khong ghi gi
    assert "preflight" in capsys.readouterr().err
