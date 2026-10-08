"""Kiem tra seed mock hop le: dung schema, khong trung, dung gia tri cho phep."""
import json
from pathlib import Path

import pytest

SEEDS = Path(__file__).resolve().parent.parent / "data" / "seeds"
CATEGORIES = {"Backend", "Frontend", "Database", "System Design", "DevOps"}
DIFFICULTIES = {"easy", "medium", "hard"}


def load(name):
    return json.loads((SEEDS / name).read_text(encoding="utf-8"))


def test_qa_seed_schema_and_uniqueness():
    items = load("qa_seed.json")
    assert len(items) >= 50
    questions = [i["question"] for i in items]
    assert len(set(questions)) == len(questions)
    for i in items:
        assert i["category"] in CATEGORIES
        assert i["difficulty"] in DIFFICULTIES
        assert i["synthetic"] is True and i["language"] == "vi"
        assert len(i["question"]) > 10 and len(i["answer"]) > 40
        assert i["tags"]
    assert {i["category"] for i in items} == CATEGORIES
    assert {i["difficulty"] for i in items} == DIFFICULTIES


@pytest.mark.parametrize("name", ["tech_notes_seed.json"])
def test_tech_notes_schema(name):
    items = load(name)
    heads = [i["heading_path"] for i in items]
    assert len(set(heads)) == len(heads)
    for i in items:
        assert i["content"].startswith(i["heading_path"])
        assert i["license"] == "own-work" and i["synthetic"] is True
