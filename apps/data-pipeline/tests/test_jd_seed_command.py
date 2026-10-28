"""Lenh seed-jobs tren DB gia (spec 009 T047, FR-019..FR-021): ma thoat, thu tu commit, idempotent, --clean."""
import argparse
import json
from datetime import datetime, timezone

import pytest

from pipeline import jd_seed_command
from pipeline.jd_gap_planner import CITIES, FLOOR_LEVELS
from pipeline.jd_seed_command import input_problems, seed_jobs
from pipeline.skill_dictionary import GROUPS

from jd_seed_fake_db import FakeDb, contract_schema

NOW = datetime(2026, 10, 28, 7, 0, tzinfo=timezone.utc)
SKILL_OF = {"backend": "python", "frontend": "react", "mobile_fullstack": "flutter", "devops": "docker", "ai_data": "pytorch"}
COMPANIES = ("Công Ty Mây Xanh", "CÔNG TY MÂY XANH", "Đất Việt Soft")  # 2 cach viet cung mot cong ty


def _jds():
    cells = [(g, lv, c) for g in GROUPS for lv in FLOOR_LEVELS for c in CITIES]
    return [{
        "jd_id": f"c{i:02d}", "title": f"Dev {i}", "company": COMPANIES[i % 3], "city": c, "work_type": "onsite",
        "level": lv, "group": g, "skills": [SKILL_OF[g]], "synthetic": False, "date_posted": "2026-10-20",
        "deadline": None, "sections": {"description": f"Mo ta {i}", "requirements": "Yeu cau"},
    } for i, (g, lv, c) in enumerate(cells)]


@pytest.fixture
def env(monkeypatch, tmp_path):
    log = []
    schema = contract_schema()
    dbs = {db: FakeDb(db, schema[db], log) for db in schema}
    jds = _jds()
    monkeypatch.setattr(jd_seed_command, "read_normalized", lambda: jds)
    monkeypatch.setattr(jd_seed_command, "JD_SEED_MANIFEST_PATH", tmp_path / "manifest.jsonl")
    return {"log": log, "user": dbs["user_db"], "job": dbs["job_db"], "jds": jds, "manifest": tmp_path / "manifest.jsonl"}


def _run(env, password_hash=lambda: "$2b$12$hash", count=10, clean=False):
    args = argparse.Namespace(count=count, clean=clean)
    return seed_jobs(args, env["user"], env["job"], password_hash, NOW)


def _inserts(env):
    return [line for line in env["log"] if line.startswith("insert")]


def test_seed_writes_user_db_first_then_postings(env):
    assert _run(env) == 0
    log = env["log"]
    assert log.index("commit user_db") < log.index("insert job_db.job_postings") < log.index("commit job_db")
    assert len(env["job"].tables["job_postings"]) == 10
    assert len(env["user"].tables["users"]) == len(env["user"].tables["company_profiles"]) == 2  # Mây Xanh gop
    assert {r["role"] for r in env["user"].tables["users"]} == {"Employer"}
    rows = [json.loads(line) for line in env["manifest"].read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 10 and all(row["inserted"] for row in rows)


def test_rerun_inserts_nothing(env):
    assert _run(env) == 0
    before = len(_inserts(env))
    assert _run(env) == 0
    assert len(_inserts(env)) == before
    rows = [json.loads(line) for line in env["manifest"].read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 10 and not any(row["inserted"] for row in rows)


def test_schema_drift_exits_2_without_writes(env):
    del env["user"].schema["company_profiles"]["company_name"]
    assert _run(env) == 2 and _inserts(env) == []


def test_missing_password_decision_blocks_seed_but_not_clean(env):
    assert _run(env, password_hash=None) == 2 and _inserts(env) == []
    assert _run(env, password_hash=None, clean=True) == 0


def test_existing_skill_with_same_name_is_reused(env):
    env["job"].tables["skills"].append({"id": "fsd-py", "name": "python", "slug": "python-fsd"})
    assert _run(env) == 0
    assert not [r for r in env["job"].tables["skills"] if r["slug"] == "python"]
    links = {r["skill_id"] for r in env["job"].tables["job_skills"]}
    assert "fsd-py" in links and len(env["job"].tables["job_skills"]) == 10


def test_clean_removes_only_seed_rows_job_db_first(env):
    assert _run(env) == 0
    env["user"].tables["users"].append({"id": "real", "email": "real@example.com"})
    env["log"].clear()
    assert _run(env, clean=True) == 0
    assert env["log"].index("commit job_db") < env["log"].index("commit user_db")
    assert [r["id"] for r in env["user"].tables["users"]] == ["real"]
    assert env["job"].tables["job_postings"] == [] and env["job"].tables["job_skills"] == []
    assert not env["manifest"].exists()


def test_bad_jd_data_exits_1_before_writes(env):
    for jd in env["jds"]:
        jd["deadline"] = "30/11/2026"
    assert _run(env) == 1 and _inserts(env) == []


def test_count_below_one_exits_1(env):
    assert _run(env, count=0) == 1 and env["log"] == []


def test_input_problems_names_unknown_skill_and_bad_date():
    jd = {"jd_id": "x1", "skills": ["python", "cobol-85"], "deadline": "2026-13-01", "date_posted": None}
    assert input_problems([jd], {"python"}) == [
        "x1: ky nang khong co trong danh muc: cobol-85",
        "x1: deadline khong dung dinh dang YYYY-MM-DD: '2026-13-01'",
    ]
