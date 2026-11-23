"""Fixture chung cho test index-jd-match (spec 017): file dau vao + DB gia + embedder gia + thu muc run report o tmp_path.

Test import `env` voi `# noqa: F401  (fixture)`, giong textbook_command_fixtures.
"""
import json

import pytest

from jd_match_fakes import FakeDb, FakeEmbedder, make_jd
from pipeline import jd_match_index_command as command
from pipeline.__main__ import main
from pipeline.settings import IndexSettings

JD, DATASET, MODEL = "job_description", "jd-match", "text-embedding-3-small"
OTHER_MODEL = "text-embedding-3-large"


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
