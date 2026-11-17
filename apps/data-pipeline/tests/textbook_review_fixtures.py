"""Fixture dung chung cho test review-textbook-prepare / review-textbook-score / coverage-textbook (spec 012 T030, T033).

`textbook_env` doi moi thu muc textbook (manifest, da xu ly, lo soat, decisions) sang tmp_path, dung manifest + catalog nho cua
tests/fixtures/textbook (nguon `valid-source`, track be_track / fe_track, tinh huong scn.be.orders / scn.fe.dashboard) va
BAN SAO file review-canaries.json that. Ban ghi da xu ly dung theo data-model §3 (chi cac truong lenh doc).
"""
import json
import shutil
from types import SimpleNamespace

import pytest

from pipeline import settings
from pipeline.qa_record_builder import content_hash

SOURCE = "valid-source"
BODY_WORDS = 50  # du dai de trim vai tu van con >= 30 tu


@pytest.fixture()
def textbook_env(tmp_path, monkeypatch, fixtures_dir):
    sources = tmp_path / "textbook_sources"
    sources.mkdir()
    for name in ("valid-source.yaml", "scenario-queries.yaml"):
        shutil.copy(fixtures_dir / "textbook" / "sources" / name, sources / name)
    shutil.copy(settings.TEXTBOOK_SOURCES_DIR / "review-canaries.json", sources / "review-canaries.json")
    env = SimpleNamespace(
        sources=sources, processed=tmp_path / "processed", work=tmp_path / "review", decisions=tmp_path / "decisions",
        canaries=json.loads((sources / "review-canaries.json").read_text(encoding="utf-8")),
    )
    monkeypatch.setattr(settings, "TEXTBOOK_SOURCES_DIR", env.sources)
    monkeypatch.setattr(settings, "TEXTBOOK_PROCESSED_DIR", env.processed)
    monkeypatch.setattr(settings, "TEXTBOOK_REVIEW_WORK_DIR", env.work)
    monkeypatch.setattr(settings, "TEXTBOOK_DECISIONS_DIR", env.decisions)
    monkeypatch.setattr(settings, "catalog_dir", lambda: fixtures_dir / "textbook" / "catalog_manifest")
    return env


def make_record(n, content=None, scenarios=("scn.be.orders",), category="Backend", tracks=("be_track",), **meta):
    """Ban ghi da xu ly toi thieu: content co dong tieu de + than >= 30 tu, hash theo content_hash cua 005."""
    if content is None:
        content = f"Example Backend Docs > Locking > Topic {n}\n\n" + " ".join(f"term{n}x{i}" for i in range(BODY_WORDS))
    return {
        "content": content, "content_hash": content_hash(content), "source_type": "textbook", "category": category,
        "metadata": {"source_id": SOURCE, "tracks": list(tracks), "scenario_ids": list(scenarios), **meta},
    }


def write_processed(env, records, source_id=SOURCE):
    env.processed.mkdir(parents=True, exist_ok=True)
    (env.processed / f"{source_id}.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")


def item_id(record):
    return record["content_hash"][:12]


def read_review_dir(env, source_id=SOURCE):
    """({batch-NN: [{item_id, content}]}, canary-key) cua lo prepare vua ghi."""
    directory = env.work / source_id
    batches = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("batch-*.json"))}
    return batches, json.loads((directory / "canary-key.json").read_text(encoding="utf-8"))


def write_judgments(env, overrides=None, source_id=SOURCE):
    """Ghi judgments-NN.jsonl: doan moi `drop nav`, doan that `keep`, tru item_id trong `overrides` (dict hoac None = bo dong)."""
    overrides = overrides or {}
    batches, key = read_review_dir(env, source_id)
    for name, items in batches.items():
        lines = []
        for entry in items:
            if entry["item_id"] in overrides:
                judgment = overrides[entry["item_id"]]
            elif entry["item_id"] in key[name]:
                judgment = {"verdict": "drop", "reason": "nav"}
            else:
                judgment = {"verdict": "keep"}
            if judgment is not None:
                lines.append(json.dumps({"item_id": entry["item_id"], **judgment}))
        (env.work / source_id / f"judgments-{name[len('batch-'):]}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
