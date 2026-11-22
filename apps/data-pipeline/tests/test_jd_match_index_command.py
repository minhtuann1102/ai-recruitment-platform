"""T005 (spec 017 US1): index-jd-match voi ket noi DB gia + embedder gia, hoan toan offline.

Chay qua main([...]) nen kiem luon parser, ma thoat va run report; I/O tro vao tmp_path.
"""
import json
from unittest.mock import Mock

import pytest

from jd_match_fakes import FakeDb, FakeEmbedder, make_jd
from pipeline import jd_match_index_command as command
from pipeline.__main__ import HANDLERS, build_parser, main
from pipeline.jd_match_text import build_match_records
from pipeline.settings import ConfigError, IndexSettings

JD, DATASET, MODEL = "job_description", "jd-match", "text-embedding-3-small"


class Env:
    """Gom file dau vao, DB gia, embedder gia (thay duoc giua hai lan chay) va thu muc run report."""

    def __init__(self, tmp_path):
        self.input, self.out = tmp_path / "jd_normalized.jsonl", tmp_path / "out"
        self.db, self.embedder, self.model = FakeDb(), FakeEmbedder(), "openai/" + MODEL

    def write_jds(self, *jds):
        self.input.write_text("".join(json.dumps(jd, ensure_ascii=False) + "\n" for jd in jds), encoding="utf-8")

    def run(self, *flags):
        return main(["index-jd-match", *flags])

    def stats(self):
        return json.loads(sorted(self.out.glob("run-report-index-jd-match-*.json"))[-1].read_text(encoding="utf-8"))["index"]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    e = Env(tmp_path)
    monkeypatch.setattr(command, "JD_NORMALIZED_PATH", e.input)
    monkeypatch.setattr(command, "PROCESSED_DIR", e.out)
    monkeypatch.setattr(command, "require_index_settings",
                        lambda: IndexSettings("k", "http://x", e.model, 1536, "postgresql://x"))
    monkeypatch.setattr(command, "EmbeddingClient", lambda settings: e.embedder)
    monkeypatch.setattr(command.psycopg, "connect", lambda url: e.db)
    return e


def two_jds():
    return [make_jd("a:1"), make_jd("a:2", title="Devops Engineer", group="devops")]


def test_duplicate_hash_keeps_first_and_stats_count_skips(env):
    env.write_jds(make_jd("a:1"), make_jd("a:2"), make_jd("a:3", group=None), make_jd("b:4", title="Khác", level="Senior"))
    assert env.run() == 0
    assert env.stats() == {
        "input": 4, "skipped_no_group": 1, "skipped_duplicate_hash": 1, "embedded": 2, "embed_errors": 0, "inserted": 2,
        "updated": 0, "deleted": 0, "skipped_other_dataset": 0, "cleanup": "done", "embedding_tokens": 6}
    rows = env.db.of(JD, DATASET).values()
    assert sorted(r["metadata"]["jd_id"] for r in rows) == ["a:1", "b:4"]
    assert {r["model"] for r in rows} == {MODEL}  # ten luu khong co tien to openai/
    assert env.embedder.probe_calls == 1  # chi probe mot lan khi co ban ghi moi


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


def test_model_mismatch_exits_one_without_embedding_or_writing(env, capsys):
    env.write_jds(*two_jds())
    env.db.seed("old1", JD, DATASET, model="text-embedding-3-large")
    assert env.run() == 1
    assert env.embedder.probe_calls == 0 and env.embedder.embed_calls == []
    assert set(env.db.rows) == {"old1"} and env.db.kinds("insert") == []
    err = capsys.readouterr().err
    assert "text-embedding-3-large" in err and MODEL in err and "--rebuild" in err
    assert list(env.out.glob("*")) == []  # chua ghi gi -> khong co run report


def test_model_check_ignores_models_of_other_datasets_and_source_types(env):
    env.write_jds(*two_jds())
    env.db.seed("qa1", "interview_qa", "de_interview_qa", model="text-embedding-3-large")
    env.db.seed("jd9", JD, "other-jd-set", model="text-embedding-3-large")
    assert env.run() == 0
    assert env.db.kinds("models") == [(JD, DATASET)]


def test_rebuild_deletes_only_jd_match_job_description_rows_then_rewrites(env):
    env.write_jds(*two_jds())
    keep = {"qa1": ("interview_qa", "de_interview_qa"), "jd9": (JD, "other-jd-set"), "tb1": ("textbook", DATASET)}
    for chash, (source_type, dataset) in keep.items():
        env.db.seed(chash, source_type, dataset)
    records, _ = build_match_records(two_jds())
    for record in records:  # cung hash voi ban ghi moi nhung model cu: neu xoa sau plan_writes thi se bi tinh la update
        env.db.seed(record["content_hash"], JD, DATASET, model="text-embedding-3-large")
    env.db.seed("stale", JD, DATASET, model="text-embedding-3-large")
    assert env.run() == 1  # chua --rebuild
    assert env.run("--rebuild") == 0
    assert env.db.kinds("delete_dataset") == [(JD, DATASET)]
    assert set(env.db.rows) >= set(keep) and "stale" not in env.db.rows
    jd_match = env.db.of(JD, DATASET)
    assert len(jd_match) == 2 and {r["model"] for r in jd_match.values()} == {MODEL}
    stats = env.stats()
    assert (stats["deleted"], stats["embedded"], stats["inserted"], stats["updated"]) == (3, 2, 2, 0)


def test_rebuild_with_matching_model_still_rewrites_dataset(env):
    env.write_jds(*two_jds())
    assert env.run() == 0
    assert env.run("--rebuild") == 0
    assert env.stats()["deleted"] == 2 and env.stats()["inserted"] == 2


def test_rebuild_probes_before_deleting(env):
    env.write_jds(*two_jds())
    env.db.seed("old1", JD, DATASET, model="text-embedding-3-large")
    env.embedder = FakeEmbedder(fail_probe=ConfigError("model tra 3 chieu"))
    assert env.run("--rebuild") == 2
    assert "old1" in env.db.rows and env.db.kinds("delete_dataset") == []


def test_embed_error_exits_three_and_does_not_clean_up(env, capsys):
    env.write_jds(*two_jds())
    env.db.seed("stale", JD, DATASET, model=MODEL)
    env.embedder = FakeEmbedder(fail_embed=True)
    assert env.run() == 3
    assert "stale" in env.db.rows and env.db.kinds("delete_cleanup") == []
    stats = env.stats()
    assert stats["embed_errors"] == 2 and stats["inserted"] == 0 and "skipped" in stats["cleanup"]


def test_limit_takes_first_n_jds_and_never_cleans_up_other_rows(env):
    env.write_jds(*two_jds(), make_jd("a:3", title="Khác", level="Senior"))
    env.db.seed("stale", JD, DATASET, model=MODEL)
    assert env.run("--limit", "1") == 0
    stats = env.stats()
    assert (stats["input"], stats["inserted"], stats["deleted"], stats["cleanup"]) == (1, 1, 0, "skipped (--limit)")
    assert "stale" in env.db.rows


def test_rebuild_together_with_limit_is_refused_before_touching_anything(env, capsys):
    env.write_jds(*two_jds())
    env.db.seed("old1", JD, DATASET)
    assert env.run("--rebuild", "--limit", "1") == 1
    assert "--limit" in capsys.readouterr().err and set(env.db.rows) == {"old1"}


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
