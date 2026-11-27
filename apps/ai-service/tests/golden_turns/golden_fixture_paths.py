"""Duong dan fixture golden, dung chung cho script ghi va test so sanh."""
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden_turns"


def fixture_path(name: str) -> Path:
    return FIXTURE_DIR / f"{name}.json"
