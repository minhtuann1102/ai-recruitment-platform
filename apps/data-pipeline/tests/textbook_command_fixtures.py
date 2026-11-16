"""Fixture chung cho test lenh textbook (crawl / process / index): thu muc du lieu rieng trong tmp_path + trang tho mau.

`textbook_env` copy valid-source.yaml + scenario-queries.yaml (3 dong trang: locking, constraints, reference voi
sections Cache / Queue), tro `settings` vao tmp_path va catalog nho cua fixture, tra Env de test tu dung file.
"""
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from pipeline import settings

SOURCE_ID = "valid-source"
BASE = "https://docs.example.org/guide/"
LOCKING, CONSTRAINTS, REFERENCE = BASE + "locking.html", BASE + "constraints.html", BASE + "reference.html"

# Doan van > 30 tu, khong phai code / danh sach link: qua duoc loc nhieu
PROSE = (
    "A row level lock stops two concurrent transactions from updating the same order at once, so the second writer "
    "waits until the first one commits or rolls back, which keeps totals consistent for every customer order."
)


@dataclass
class Env:
    sources_dir: Path
    raw_dir: Path
    processed_dir: Path
    decisions_dir: Path

    def write_raw(self, pages, name="20261116T080000Z.jsonl", source_id=SOURCE_ID) -> Path:
        path = self.raw_dir / source_id / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(p) + "\n" for p in pages), encoding="utf-8")
        return path


def page(url, title, *sections):
    """sections: (heading_path, text)."""
    return {
        "source_id": SOURCE_ID, "url": url, "title": title, "crawled_at": "2026-11-16T08:00:00+00:00",
        "sections": [{"heading_path": list(h), "text": t} for h, t in sections],
    }


@pytest.fixture()
def textbook_env(tmp_path, monkeypatch, fixtures_dir):
    env = Env(tmp_path / "sources", tmp_path / "raw", tmp_path / "processed", tmp_path / "decisions")
    env.sources_dir.mkdir()
    for name in ("valid-source.yaml", "scenario-queries.yaml"):
        shutil.copy(fixtures_dir / "textbook" / "sources" / name, env.sources_dir / name)
    monkeypatch.setattr(settings, "TEXTBOOK_SOURCES_DIR", env.sources_dir)
    monkeypatch.setattr(settings, "TEXTBOOK_RAW_DIR", env.raw_dir)
    monkeypatch.setattr(settings, "TEXTBOOK_PROCESSED_DIR", env.processed_dir)
    monkeypatch.setattr(settings, "TEXTBOOK_DECISIONS_DIR", env.decisions_dir)
    monkeypatch.setattr(settings, "catalog_dir", lambda: fixtures_dir / "textbook" / "catalog_manifest")
    return env
