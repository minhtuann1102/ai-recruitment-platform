from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture()
def sample_catalog_dir() -> Path:
    """Catalog nho (2 topic + 1 scenario) de test khong phu thuoc catalog that cua ai-service."""
    return FIXTURES_DIR / "catalog"
