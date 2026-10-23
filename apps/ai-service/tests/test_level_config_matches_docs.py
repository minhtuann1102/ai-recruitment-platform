"""Doi chieu LEVEL_CONFIG voi bang do kho trong docs/ai-service/01 muc 2.1 (nguon su that la tai lieu)."""
import re
from pathlib import Path

import pytest

from app.models_common import LEVEL_CONFIG

DOC = Path(__file__).resolve().parents[3] / "docs" / "ai-service" / "01-input-schema-and-cv-processing.md"
NAMES = {"Fresher": "fresher", "Junior": "junior", "Middle": "middle", "Senior": "senior"}


def documented():
    rows = re.findall(r"^\| (Fresher|Junior|Middle|Senior) \| (\d) \| (\d)–(\d) \|", DOC.read_text(encoding="utf-8"), re.M)
    return {NAMES[n]: {"start": int(s), "bounds": (int(lo), int(hi))} for n, s, lo, hi in rows}


def test_doc_table_is_found():
    assert set(documented()) == set(LEVEL_CONFIG)


@pytest.mark.parametrize("level", list(LEVEL_CONFIG))
def test_bounds_and_start_match_docs(level):
    doc = documented()[level]
    assert LEVEL_CONFIG[level]["bounds"] == doc["bounds"]
    assert LEVEL_CONFIG[level]["start"] == doc["start"]
    lo, hi = doc["bounds"]
    assert lo <= doc["start"] <= hi
