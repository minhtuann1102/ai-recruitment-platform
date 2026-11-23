"""Kiem bo CV ung vien tong hop cho demo goi y hai chieu (spec 017 T040): schema, phan bo, ky nang, khong PII."""
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from pipeline.skill_dictionary import load_skill_dictionary

PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "candidates" / "candidate_cvs.json"
TRACKS = {"java_backend", "python_backend", "nodejs_backend", "frontend_react", "devops_engineer", "ai_engineer"}
LEVEL_YEARS = {"fresher": (0.0, 0.99), "junior": (1.0, 2.99), "middle": (3.0, 4.99), "senior": (5.0, 15.0)}
LEVEL_COUNT = {"fresher": 3, "junior": 4, "middle": 4, "senior": 3}
SKILL_CATEGORIES = {"language", "framework", "database", "devops", "tool", "concept"}
EVIDENCE = {"work", "project", "education", "listed"}
COMPANY_TYPES = {"product", "outsource", "startup", "other", "unknown"}
PII = re.compile(r"@|https?://|www\.|\d{9,}")


@pytest.fixture(scope="module")
def candidates():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_size_and_unique_ids(candidates):
    assert len(candidates) == 84
    assert len({c["candidate_id"] for c in candidates}) == 84
    assert len({c["cv_profile"]["headline"] for c in candidates}) == 84


def test_level_mix_per_track(candidates):
    for track in TRACKS:
        levels = Counter(c["level"] for c in candidates if c["track"] == track)
        assert dict(levels) == LEVEL_COUNT, track
    assert {c["track"] for c in candidates} == TRACKS


def test_years_match_level_and_open_flag(candidates):
    for c in candidates:
        low, high = LEVEL_YEARS[c["level"]]
        assert low <= c["cv_profile"]["total_years_experience"] <= high, c["candidate_id"]
        assert isinstance(c["is_open_to_work"], bool)
    open_ratio = sum(c["is_open_to_work"] for c in candidates) / len(candidates)
    assert 0.55 <= open_ratio <= 0.85


def test_profile_shape_and_enums(candidates):
    for c in candidates:
        p = c["cv_profile"]
        assert p["headline"].strip()
        assert 1 <= len(p["skills"]) <= 25 and len(p["experiences"]) <= 8 and len(p["projects"]) <= 6
        assert all(s["category"] in SKILL_CATEGORIES and s["evidence"] in EVIDENCE for s in p["skills"])
        assert all(e.get("company_type", "unknown") in COMPANY_TYPES for e in p["experiences"])


def test_every_skill_and_tech_is_in_dictionary(candidates):
    dictionary = load_skill_dictionary()
    unknown = set()
    for c in candidates:
        p = c["cv_profile"]
        names = [s["name"] for s in p["skills"]]
        names += [t for e in p["experiences"] for t in e.get("tech", [])]
        names += [t for pr in p["projects"] for t in pr.get("tech", [])]
        unknown |= {n for n in names if dictionary.canonical(n) is None}
    assert not unknown


def test_no_contact_details(candidates):
    assert not [c["candidate_id"] for c in candidates if PII.search(json.dumps(c["cv_profile"], ensure_ascii=False))]
