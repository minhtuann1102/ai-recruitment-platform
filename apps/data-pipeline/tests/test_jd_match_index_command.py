"""T005 (spec 017 US1): index-jd-match voi ket noi DB gia + embedder gia, hoan toan offline.

Luong chinh, loi dau vao va parser. Model guard / --rebuild / --limit / loi embed: test_jd_match_index_modes.py.
Chay qua main([...]) nen kiem luon parser, ma thoat va run report; I/O tro vao tmp_path.
"""
from unittest.mock import Mock

from jd_match_command_fixtures import DATASET, JD, MODEL, command, env, two_jds  # noqa: F401  (fixture)
from jd_match_fakes import FakeEmbedder, make_jd
from pipeline.__main__ import HANDLERS, build_parser
from pipeline.settings import ConfigError


def test_duplicate_hash_is_counted_and_stats_have_every_contract_key(env):
    env.write_jds(make_jd("a:1"), make_jd("a:2"), make_jd("a:3", group=None), make_jd("b:4", title="Khác", level="Senior"))
    assert env.run() == 0
    assert env.stats() == {
        "input": 4, "skipped_no_group": 1, "skipped_duplicate_hash": 1, "by_group": {"backend": 2}, "embedded": 2, "embed_errors": 0, "inserted": 2,
        "updated": 0, "deleted": 0, "skipped_other_dataset": 0, "cleanup": "done", "embedding_tokens": 6}
    rows = env.db.of(JD, DATASET).values()
    assert sorted(r["metadata"]["jd_id"] for r in rows) == ["a:1", "b:4"]
    assert {r["model"] for r in rows} == {MODEL}  # ten luu khong co tien to openai/
    assert env.embedder.probe_calls == 1  # chi probe mot lan khi co ban ghi moi


def test_stats_count_indexed_records_by_group_including_mobile_fullstack(env):
    env.write_jds(make_jd("a:1"), make_jd("a:2", title="Mobile", group="mobile_fullstack"),
                  make_jd("a:3", title="Android", group="mobile_fullstack"), make_jd("a:4", title="Khác", group=None))
    assert env.run() == 0
    assert env.stats()["by_group"] == {"backend": 1, "mobile_fullstack": 2}  # group null khong dem (skipped_no_group)


def test_second_run_embeds_nothing_and_inserts_nothing(env):
    env.write_jds(*two_jds())
    assert env.run() == 0
    env.embedder = FakeEmbedder()
    assert env.run() == 0
    assert env.embedder.probe_calls == 0 and env.embedder.embed_calls == []
    stats = env.stats()
    assert (stats["embedded"], stats["inserted"], stats["updated"], stats["embedding_tokens"]) == (0, 0, 2, 0)


def test_changed_jd_is_inserted_and_old_hash_cleaned(env):
    env.write_jds(*two_jds())
    assert env.run() == 0
    env.write_jds(make_jd("a:1"), make_jd("a:2", title="Devops Engineer", group="devops", level="Senior"))
    assert env.run() == 0
    stats = env.stats()
    assert (stats["embedded"], stats["inserted"], stats["updated"], stats["deleted"]) == (1, 1, 1, 1)
    assert len(env.db.of(JD, DATASET)) == 2


def test_no_indexable_jd_exits_one_and_rebuild_does_not_wipe_dataset(env, capsys):
    env.write_jds(make_jd("a:1", group=None))
    env.db.seed("old1", JD, DATASET)
    assert env.run("--rebuild") == 1
    assert "old1" in env.db.rows and env.db.kinds("delete_dataset") == []


def test_missing_input_file_is_exit_one_before_needing_env(env, monkeypatch, capsys):
    monkeypatch.setattr(command, "JD_NORMALIZED_PATH", env.input.parent / "missing.jsonl")
    monkeypatch.setattr(command, "require_index_settings", Mock(side_effect=AssertionError("khong duoc doc cau hinh")))
    assert env.run() == 1
    assert "process-jd" in capsys.readouterr().err


def test_bad_json_line_is_exit_one_not_a_traceback(env, capsys):
    env.input.write_text('{"jd_id": "a:1"}\nnot json\n', encoding="utf-8")
    assert env.run() == 1
    err = capsys.readouterr().err
    assert "jd_normalized.jsonl:2" in err and "Traceback" not in err


def test_missing_settings_is_exit_two(env, monkeypatch, capsys):
    env.write_jds(*two_jds())

    monkeypatch.setattr(command, "require_index_settings", Mock(side_effect=ConfigError("thieu bien moi truong: AI_DB_URL")))
    assert env.run() == 2
    assert "preflight" in capsys.readouterr().err and env.db.rows == {}


def test_parser_registers_command_with_flags():
    args = build_parser().parse_args(["index-jd-match", "--rebuild", "--limit", "5"])
    assert (args.command, args.rebuild, args.limit) == ("index-jd-match", True, 5)
    defaults = build_parser().parse_args(["index-jd-match"])
    assert (defaults.rebuild, defaults.limit) == (False, None)
    assert HANDLERS["index-jd-match"] is command.run_index_jd_match
