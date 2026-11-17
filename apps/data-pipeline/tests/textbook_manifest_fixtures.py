"""Fixture dung chung cho test manifest textbook (test_textbook_source_manifest, test_textbook_manifest_page_rules).

Nguon hop le nam o tests/fixtures/textbook/sources/valid-source.yaml; `check` ghi mot ban sao co MOT loi toi thieu vao
thu muc rieng moi lan goi (tmp_path) roi chay validate_sources voi catalog nho tests/fixtures/textbook/catalog_manifest.
"""
import pytest
import yaml

from pipeline.textbook_catalog_tracks import load_tracks
from pipeline.textbook_source_manifest import load_scenario_queries, load_sources, validate_sources

SOURCES_FIXTURE = "textbook/sources"
VALID_NAME = "valid-source"


@pytest.fixture()
def tracks(fixtures_dir):
    return load_tracks([fixtures_dir / "textbook" / "catalog_manifest"])


@pytest.fixture()
def valid(fixtures_dir):
    return yaml.safe_load((fixtures_dir / SOURCES_FIXTURE / "valid-source.yaml").read_text(encoding="utf-8"))


@pytest.fixture()
def queries(fixtures_dir):
    return load_scenario_queries(fixtures_dir / SOURCES_FIXTURE)


@pytest.fixture()
def check(tmp_path, tracks, queries):
    """check(doc, other=(name, doc), queries=...) -> (errors, warnings) sau khi ghi cac file vao thu muc rieng."""

    runs = []

    def run(doc, name=VALID_NAME, extra=None, query_override=None):
        directory = tmp_path / f"run{len(runs)}"  # moi lan goi mot thu muc rieng, file cu khong lan sang
        directory.mkdir()
        runs.append(directory)
        for file_name, content in [(name, doc)] + ([extra] if extra else []):
            (directory / f"{file_name}.yaml").write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
        sources = load_sources(directory)
        return validate_sources(sources, tracks, queries if query_override is None else query_override)

    return run


def only_error(result, *needles):
    errors, _ = result
    assert len(errors) == 1, errors
    assert ".yaml" in errors[0], errors[0]  # moi loi nguon / trang nam ten file manifest
    assert all(n in errors[0] for n in needles), errors[0]
