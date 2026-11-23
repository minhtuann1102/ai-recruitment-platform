"""017 R6: ai-service giu ban sao skill_dictionary.yaml (Docker build context khong doc duoc file cua pipeline).
Hai ban lech nhau thi test do: sua ban goc o pipeline roi chep sang ai-service."""
from pathlib import Path

from pipeline.settings import SKILL_DICTIONARY_PATH

COPY_PATH = Path(__file__).resolve().parents[2] / "ai-service" / "app" / "matching" / "skill_dictionary.yaml"


def _read(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")  # core.autocrlf=true tren Windows khong lam test do


def test_ai_service_copy_exists():
    assert COPY_PATH.is_file(), f"thieu ban sao {COPY_PATH}"


def test_copy_matches_the_009_source_of_truth():
    assert _read(COPY_PATH) == _read(SKILL_DICTIONARY_PATH), (
        "app/matching/skill_dictionary.yaml lech voi apps/data-pipeline/data/seeds/skill_dictionary.yaml; "
        "chep ban goc sang ai-service (spec 017 research R6)")
