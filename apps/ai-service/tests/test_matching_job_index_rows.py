"""017 US2 T015: parse dong ai_db (embedding::text, metadata) thanh snapshot da chuan hoa L2; chi muc mau mock."""
import logging
from datetime import date, datetime, timezone

import numpy as np
import pytest

from app.matching.hash_embedder import EMBEDDING_DIMS
from app.matching.job_index import build_mock_snapshot, rows_to_snapshot
from fakes.fake_match_index import meta, vec_text

# --- parse dong ai_db -----------------------------------------------------------------------------------------

def test_rows_become_a_normalized_snapshot():
    rows = [(vec_text(3, 4), meta("jd:1")),
            (vec_text(0, 0, 2), meta("jd:2", level=None, deadline=None, skills=[], title="T2", group="devops"))]
    snap = rows_to_snapshot(rows, "text-embedding-3-small", datetime(2026, 11, 22, tzinfo=timezone.utc))
    assert [j.job_id for j in snap.jobs] == ["jd:1", "jd:2"] and snap.source == "ai_db"
    assert snap.matrix.shape == (2, EMBEDDING_DIMS)
    assert snap.matrix[0, :2].tolist() == pytest.approx([0.6, 0.8]) and snap.matrix[1, 2] == pytest.approx(1.0)
    assert np.linalg.norm(snap.matrix, axis=1) == pytest.approx([1.0, 1.0])
    one, two = snap.jobs
    assert (one.title, one.group, one.level, one.level_rank, one.deadline) == (
        "Backend Developer (Java)", "backend", "Mid", 2, date(2030, 12, 1))
    assert one.skills == frozenset({"java", "kafka"})
    assert (two.level, two.level_rank, two.deadline, two.skills, two.group) == (None, None, None, frozenset(), "devops")
    assert snap.embedding_model == "text-embedding-3-small" and len(snap) == 2


def test_duplicate_jd_id_keeps_the_first_row():
    rows = [(vec_text(1), meta("jd:1", title="moi")), (vec_text(0, 1), meta("jd:1", title="cu")),
            (vec_text(0, 0, 1), meta("jd:2"))]
    snap = rows_to_snapshot(rows, "m", datetime.now(timezone.utc))
    assert [(j.job_id, j.title) for j in snap.jobs] == [("jd:1", "moi"), ("jd:2", "Backend Developer (Java)")]
    assert snap.matrix.shape[0] == 2 and snap.matrix[0, 0] == pytest.approx(1.0)


def test_malformed_rows_are_skipped_and_counted(caplog):
    rows = [(vec_text(1), meta("ok")),
            (vec_text(1), meta(jd_id=None)),  # thieu jd_id
            (vec_text(1), meta("nogroup", group=None)),
            ("[1,2,3]", meta("shortvec")),  # sai so chieu
            ("not a vector", meta("garbage")),
            (vec_text(0), meta("zerovec")),  # vector 0 khong chuan hoa duoc
            (vec_text(1), "metadata-khong-phai-dict")]
    with caplog.at_level(logging.WARNING, logger="ai_service.matching"):
        snap = rows_to_snapshot(rows, "m", datetime.now(timezone.utc))
    assert [j.job_id for j in snap.jobs] == ["ok"] and snap.matrix.shape == (1, EMBEDDING_DIMS)
    assert "match_index_rows_skipped count=6" in caplog.text


def test_bad_deadline_text_becomes_no_deadline():
    snap = rows_to_snapshot([(vec_text(1), meta("a", deadline="sap het han"))], "m", datetime.now(timezone.utc))
    assert snap.jobs[0].deadline is None


def test_empty_result_gives_empty_snapshot_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="ai_service.matching"):
        snap = rows_to_snapshot([], "text-embedding-3-small", datetime.now(timezone.utc))
    assert len(snap) == 0 and snap.matrix.shape == (0, EMBEDDING_DIMS)
    assert "match_index_empty" in caplog.text


# --- mock ---

def test_mock_snapshot_loads_mock_jobs_with_hash_vectors():
    snap = build_mock_snapshot(datetime(2026, 11, 22, tzinfo=timezone.utc))
    assert snap.source == "mock" and len(snap) == 14 and snap.matrix.shape == (14, EMBEDDING_DIMS)
    assert np.linalg.norm(snap.matrix, axis=1) == pytest.approx([1.0] * 14)
    by_id = {j.job_id: j for j in snap.jobs}
    assert by_id["mock:backend-java-mid"].level_rank == 2 and by_id["mock:backend-java-no-level"].level_rank is None
    assert by_id["mock:backend-java-expired"].deadline == date(2020, 6, 30)
    assert by_id["mock:devops-manager"].skills == frozenset()
    assert snap.embedding_model.startswith("mock")
