"""T026: check_ready (khong can DB) + index-textbook tu choi offline khi chua duyet / chua soat / quyet dinh da doi.
Phan DB kiem o quickstart §5."""
import json

from pipeline.__main__ import main
from pipeline import textbook_index_command
from pipeline.textbook_index_command import check_ready
from pipeline.textbook_review_decisions import Decisions, decisions_path, save_decisions
from textbook_command_fixtures import CONSTRAINTS, LOCKING, PROSE, REFERENCE, SOURCE_ID, page, textbook_env  # noqa: F401  (fixture)

KEEP, DROP = {"verdict": "keep"}, {"verdict": "drop", "reason": "nav"}
GATE = "auto:canary-gate"


def _record(h, review=None, original=None):
    metadata = {"dataset": "de_textbook_valid-source"}
    if review:
        metadata["review"] = review
    if original:
        metadata["original_hash"] = original
    return {"content": f"T > H\n\n{h}", "content_hash": h, "metadata": metadata}


def _approved(**by_hash):
    return Decisions(SOURCE_ID, "2026-11-16", GATE, dict(by_hash))


def test_ready_when_approved_and_every_record_reviewed_with_matching_decision():
    records = [_record("h1", "keep"), _record("h2", "trimmed", original="h0")]
    decisions = _approved(h1=KEEP, h0={"verdict": "trim", "remove": ["x"]})
    assert check_ready(records, decisions) == []


def test_empty_approved_by_is_reported():
    problems = check_ready([_record("h1", "keep")], Decisions(SOURCE_ID, decisions={"h1": KEEP}))
    assert len(problems) == 1 and "approved_by" in problems[0]
    blank = Decisions(SOURCE_ID, approved_by="  ", decisions={"h1": KEEP})
    assert len(check_ready([_record("h1", "keep")], blank)) == 1


def test_unreviewed_record_is_reported_with_count_and_hash():
    problems = check_ready([_record("h1", "keep"), _record("h2"), _record("h3")], _approved(h1=KEEP))
    assert len(problems) == 1 and "2 doan chua co quyet dinh soat" in problems[0] and "h2" in problems[0]


def test_both_problems_are_listed():
    assert len(check_ready([_record("h1")], Decisions(SOURCE_ID))) == 2


def test_record_whose_decision_is_now_drop_or_missing_is_reported_with_its_hash():
    """M1: decisions doi sau process-textbook (hash nay gio drop / bi xoa) -> khong duoc index doan do."""
    records = [_record("h1", "keep"), _record("h2", "keep"), _record("h3", "keep")]
    problems = check_ready(records, _approved(h1=KEEP, h2=DROP))
    assert len(problems) == 1 and "2 doan khong khop quyet dinh hien tai" in problems[0]
    assert "h2 (quyet dinh nay: drop)" in problems[0] and "h3 (quyet dinh nay: thieu)" in problems[0]
    assert "h1" not in problems[0] and "process-textbook" in problems[0]


def test_stale_check_uses_original_hash_and_flags_keep_trim_flips():
    trimmed = _record("final", "trimmed", original="orig")
    assert check_ready([trimmed], _approved(orig=KEEP))  # trim -> keep: doan da cat khong con khop
    assert check_ready([trimmed], _approved(final=KEEP))  # khoa la hash goc, khong phai hash sau trim
    assert check_ready([_record("h1", "keep")], _approved(h1={"verdict": "trim", "remove": ["x"]}))


def _process(textbook_env):
    textbook_env.write_raw([
        page(LOCKING, "Locking", (["Row locks"], PROSE)),
        page(CONSTRAINTS, "Constraints", (["Unique"], PROSE)),
        page(REFERENCE, "Reference", (["Cache"], PROSE), (["Queue"], PROSE)),
    ])
    assert main(["process-textbook", "--source", SOURCE_ID]) == 0
    path = textbook_env.processed_dir / f"{SOURCE_ID}.jsonl"
    return path, [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _approve_all_as_keep(textbook_env, rows):
    save_decisions(Decisions(SOURCE_ID, "2026-11-16", GATE, {r["content_hash"]: KEEP for r in rows}),
                   textbook_env.decisions_dir)
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
    _, rows = _process(textbook_env)
    _approve_all_as_keep(textbook_env, rows)
    for name in ("EMBEDDING_API_KEY", "LLM_API_KEY", "AI_DB_URL"):
        monkeypatch.delenv(name, raising=False)
    assert main(["index-textbook", "--source", SOURCE_ID]) == 2  # san sang; dung o cau hinh thieu (preflight), khong ghi gi
    assert "preflight" in capsys.readouterr().err


def test_command_refuses_when_decisions_changed_after_process(textbook_env, capsys, monkeypatch):
    """M1 qua main(): hash vua duoc doi thanh drop nhung chua process lai -> thoat 1, liet ke hash, khong can .env / DB."""
    _, rows = _process(textbook_env)
    _approve_all_as_keep(textbook_env, rows)
    changed = {r["content_hash"]: KEEP for r in rows}
    changed[rows[0]["content_hash"]] = DROP
    save_decisions(Decisions(SOURCE_ID, "2026-11-17", GATE, changed), textbook_env.decisions_dir)
    monkeypatch.delenv("AI_DB_URL", raising=False)
    capsys.readouterr()
    assert main(["index-textbook", "--source", SOURCE_ID]) == 1
    err = capsys.readouterr().err
    assert "khong khop quyet dinh hien tai" in err and rows[0]["content_hash"] in err and "drop" in err


def test_processed_row_missing_content_hash_is_a_clean_exit_one_not_a_traceback(textbook_env, capsys):
    """M4: index doc qua read_processed -> dong thieu content_hash = loi ro rang, khong KeyError."""
    path, rows = _process(textbook_env)
    del rows[1]["content_hash"]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert main(["index-textbook", "--source", SOURCE_ID]) == 1
    err = capsys.readouterr().err
    assert "ban ghi thu 2 thieu content / content_hash" in err and "Traceback" not in err


def test_decisions_file_copied_from_another_source_is_refused(textbook_env, capsys):
    """L5: decisions ghi source_id khac -> thoat 1."""
    _, rows = _process(textbook_env)
    _approve_all_as_keep(textbook_env, rows)
    file = decisions_path(SOURCE_ID, textbook_env.decisions_dir)
    file.write_text(file.read_text(encoding="utf-8").replace(f'"source_id": "{SOURCE_ID}"', '"source_id": "other"'),
                    encoding="utf-8")
    capsys.readouterr()
    assert main(["index-textbook", "--source", SOURCE_ID]) == 1
    assert "'other'" in capsys.readouterr().err


def test_plan_writes_value_error_is_exit_one_not_a_traceback_or_preflight(monkeypatch, capsys):
    """L1: loi du lieu tu plan_writes (dataset tron nhieu source_type) -> 1, khong phai 2 (preflight)."""
    monkeypatch.setattr(textbook_index_command, "preflight", lambda conn: None)
    monkeypatch.setattr(textbook_index_command, "_counts_by_source_type", lambda conn: {})
    monkeypatch.setattr(textbook_index_command, "_stray_textbook_datasets", lambda conn, known: [])
    monkeypatch.setattr(textbook_index_command, "existing_hashes", lambda conn, hashes: {})

    def boom(records, existing):
        raise ValueError("dataset x tron source_type")

    monkeypatch.setattr(textbook_index_command, "plan_writes", boom)
    code = textbook_index_command.index_textbook_records(None, [_record("h1", "keep")], None, None, "m", [])
    assert code == 1 and "dataset x tron source_type" in capsys.readouterr().err
