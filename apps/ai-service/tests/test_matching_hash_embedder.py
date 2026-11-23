"""017 US2 T022: embedding bam token (mock) va chi muc JD mau mock_jobs.json."""
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

import app.matching as matching_pkg
from app.matching.hash_embedder import EMBEDDING_DIMS, hash_embed
from app.matching.levels_tracks import TRACK_GROUPS
from app.matching.skill_normalizer import normalize

MOCK_JOBS = json.loads((Path(matching_pkg.__file__).parent / "mock_jobs.json").read_text(encoding="utf-8"))


def cos(a, b):
    return float(np.dot(a, b))


def test_vector_is_1536_dims_l2_normalized_float():
    v = hash_embed("Backend Developer Java Spring Boot")
    assert EMBEDDING_DIMS == 1536 and v.shape == (1536,) and v.dtype == np.float64
    assert abs(np.linalg.norm(v) - 1.0) < 1e-12


def test_same_text_same_vector_and_case_and_punctuation_insensitive():
    a = hash_embed("Java, Spring Boot!")
    assert np.array_equal(a, hash_embed("Java, Spring Boot!"))
    assert np.array_equal(a, hash_embed("  java   spring boot "))


def test_deterministic_across_processes_with_different_hash_seeds():
    code = ("from app.matching.hash_embedder import hash_embed;import hashlib;"
            "print(hashlib.md5(hash_embed('Backend Java Spring').tobytes()).hexdigest())")
    out = set()
    for seed in ("1", "2"):  # hash() mac dinh cua Python doi theo tien trinh: embedding khong duoc dung no
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out.add(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True,
                               cwd=Path(__file__).resolve().parents[1]).stdout.strip())
    assert len(out) == 1


def test_related_texts_are_closer_than_unrelated():
    cv = hash_embed("Backend Developer Java Spring Boot REST API PostgreSQL")
    related = hash_embed("Backend Developer Java Spring Boot microservices")
    unrelated = hash_embed("Frontend Developer React TypeScript CSS responsive UI")
    assert cos(cv, related) > cos(cv, unrelated) + 0.2
    assert abs(cos(cv, cv) - 1.0) < 1e-12


def test_empty_or_symbol_only_text_gives_zero_vector_not_nan():
    for text in ("", "   ", "!!! ... ---"):
        v = hash_embed(text)
        assert v.shape == (1536,) and not v.any() and not np.isnan(v).any()


def test_custom_dims():
    assert hash_embed("java", dims=64).shape == (64,)


# --- mock_jobs.json -------------------------------------------------------------------------------------------

def metas():
    return [row["metadata"] for row in MOCK_JOBS]


def test_mock_jobs_have_the_ai_db_row_shape():
    assert 10 <= len(MOCK_JOBS) <= 14
    for row in MOCK_JOBS:
        assert set(row) == {"content", "metadata"}
        assert set(row["metadata"]) == {"dataset", "chunk_type", "jd_id", "title", "group", "level", "deadline",
                                        "skills", "synthetic"}
        assert row["metadata"]["dataset"] == "jd-match" and row["metadata"]["chunk_type"] == "jd_match_summary"
        assert row["metadata"]["synthetic"] is True  # tu soan, khong lay tu crawl
        assert 0 < len(row["content"]) <= 1200 and row["metadata"]["title"] in row["content"]
    assert len({m["jd_id"] for m in metas()}) == len(MOCK_JOBS)


def test_mock_jobs_cover_four_groups_all_levels_one_expired_one_without_level():
    assert {m["group"] for m in metas()} == {"backend", "frontend", "devops", "ai_data"}
    assert {m["group"] for m in metas()} <= set(TRACK_GROUPS.values())
    levels = {m["level"] for m in metas()}
    assert {"Intern", "Junior", "Mid", "Senior", "Lead", "Manager", None} <= levels
    deadlines = [date.fromisoformat(m["deadline"]) for m in metas()]
    assert sum(d < date(2026, 11, 21) for d in deadlines) == 1  # dung mot JD het han
    assert min(d for d in deadlines if d >= date(2026, 11, 21)) >= date(2029, 1, 1)  # con lai khong het han som
    assert sum(m["level"] is None for m in metas()) == 1


def test_mock_job_skills_are_slugs_of_the_dictionary_and_not_in_the_embed_text():
    for row in MOCK_JOBS:
        skills = row["metadata"]["skills"]
        assert skills == sorted(skills) and normalize(skills) == (skills, 0)
        assert "Kỹ năng" not in row["content"]  # R4: khong dua danh sach ky nang vao van ban embed


def test_mock_index_lets_a_java_cv_find_java_jobs_first():
    cv = hash_embed("Backend Developer Java\nBackend Developer — REST API Spring Boot cho he thong thanh toan")
    ranked = sorted(MOCK_JOBS, key=lambda r: -cos(cv, hash_embed(r["content"])))
    assert "Java" in ranked[0]["metadata"]["title"] and ranked[0]["metadata"]["group"] == "backend"
