"""T005 (spec 017 US1): index-jd-match kiem model, --rebuild, --limit va loi embed (DB gia + embedder gia, offline)."""
from jd_match_command_fixtures import DATASET, JD, MODEL, OTHER_MODEL, env, two_jds  # noqa: F401  (fixture)
from jd_match_fakes import FakeEmbedder, make_jd
from pipeline.jd_match_text import build_match_records
from pipeline.settings import ConfigError


def test_model_mismatch_exits_one_without_embedding_or_writing(env, capsys):
    env.write_jds(*two_jds())
    env.db.seed("old1", JD, DATASET, model=OTHER_MODEL)
    assert env.run() == 1
    assert env.embedder.probe_calls == 0 and env.embedder.embed_calls == []
    assert set(env.db.rows) == {"old1"} and env.db.kinds("insert") == []
    err = capsys.readouterr().err
    assert OTHER_MODEL in err and MODEL in err and "--rebuild" in err
    assert list(env.out.glob("*")) == []  # chua ghi gi -> khong co run report


def test_model_check_ignores_models_of_other_datasets_and_source_types(env):
    env.write_jds(*two_jds())
    env.db.seed("qa1", "interview_qa", "de_interview_qa", model=OTHER_MODEL)
    env.db.seed("jd9", JD, "other-jd-set", model=OTHER_MODEL)
    assert env.run() == 0
    assert env.db.kinds("models") == [(JD, DATASET)]


def test_rebuild_deletes_only_jd_match_job_description_rows_then_rewrites(env):
    env.write_jds(*two_jds())
    keep = {"qa1": ("interview_qa", "de_interview_qa"), "jd9": (JD, "other-jd-set"), "tb1": ("textbook", DATASET)}
    for chash, (source_type, dataset) in keep.items():
        env.db.seed(chash, source_type, dataset)
    records, _ = build_match_records(two_jds())
    for record in records:  # cung hash voi ban ghi moi nhung model cu: neu xoa sau plan_writes thi se bi tinh la update
        env.db.seed(record["content_hash"], JD, DATASET, model=OTHER_MODEL)
    env.db.seed("stale", JD, DATASET, model=OTHER_MODEL)
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
    env.db.seed("old1", JD, DATASET, model=OTHER_MODEL)
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


def test_embed_error_under_limit_keeps_the_embed_error_cleanup_reason(env):
    env.write_jds(*two_jds())
    env.embedder = FakeEmbedder(fail_embed=True)
    assert env.run("--limit", "1") == 3
    assert env.stats()["cleanup"] == "skipped (embed_errors > 0)"


def test_embed_error_after_rebuild_hints_to_rerun_without_rebuild(env, capsys):
    env.write_jds(*two_jds())
    env.embedder = FakeEmbedder(fail_embed=True)
    assert env.run("--rebuild") == 3
    assert "khong can --rebuild" in capsys.readouterr().err
    env.embedder = FakeEmbedder()
    assert env.run() == 0  # chay lai khong --rebuild: model khop (dataset rong), ghi du
    assert len(env.db.of(JD, DATASET)) == 2


def test_embed_error_without_rebuild_has_no_rebuild_hint(env, capsys):
    env.write_jds(*two_jds())
    env.embedder = FakeEmbedder(fail_embed=True)
    assert env.run() == 3
    assert "khong can --rebuild" not in capsys.readouterr().err
