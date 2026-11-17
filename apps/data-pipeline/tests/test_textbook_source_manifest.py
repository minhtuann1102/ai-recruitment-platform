"""pipeline/textbook_source_manifest: doc manifest + luat loi cap nguon (giay phep, trang thai, source_id), contract §2.

Fixture dung chung o tests/textbook_manifest_fixtures.py; luat cap trang va canh bao o test_textbook_manifest_page_rules.
"""
import pytest

from pipeline.textbook_source_manifest import (
    ALLOWED_LICENSES,
    ManifestError,
    dataset_name,
    is_open_license,
    load_scenario_queries,
    load_sources,
)
from textbook_manifest_fixtures import SOURCES_FIXTURE, VALID_NAME, check, only_error, queries, tracks, valid  # noqa: F401


def test_valid_fixture_has_no_errors_and_no_warnings(check, valid):
    assert check(valid) == ([], [])


def test_loader_reads_fixture_dir_without_scenario_queries(fixtures_dir):
    sources = load_sources(fixtures_dir / SOURCES_FIXTURE)
    assert [s.source_id for s in sources] == [VALID_NAME]  # scenario-queries.yaml khong phai nguon
    source = sources[0]
    assert source.license_checked == "2026-11-16" and source.language == "en" and len(source.pages) == 3
    assert source.pages[2].sections == ["Cache", "Queue"]
    assert dataset_name("postgresql") == "de_textbook_postgresql"


def test_empty_or_missing_dir_gives_no_sources_and_no_queries(tmp_path):
    assert load_sources(tmp_path) == [] and load_scenario_queries(tmp_path) == {}
    assert load_sources(tmp_path / "chua-co") == []


def test_broken_yaml_is_manifest_error(tmp_path):
    (tmp_path / "broken.yaml").write_text("source_id: [unclosed\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="broken.yaml"):
        load_sources(tmp_path)


def test_source_id_must_match_file_name_and_pattern(check, valid):
    only_error(check(valid, name="other"), "source_id", "other.yaml")
    bad = {**valid, "source_id": "Bad_ID"}
    only_error(check(bad, name="Bad_ID"), "source_id", "[a-z0-9-]+")


def test_missing_required_field(check, valid):
    del valid["name"]
    only_error(check(valid), "thieu truong bat buoc 'name'")


def test_license_class_must_be_open_or_restricted(check, valid):
    valid["license_class"] = "free"
    only_error(check(valid), "license_class", "free")


def test_open_class_needs_license_in_open_list(check, valid):
    valid["license"] = "LicenseRef-Vendor-Docs"
    only_error(check(valid), "license_class open", "LicenseRef-Vendor-Docs")


def test_restricted_class_rejects_open_license(check, valid):
    valid["license_class"] = "restricted"
    only_error(check(valid), "license_class restricted", "MIT")


def test_restricted_noassertion_is_valid(check, valid):
    valid.update(license="NOASSERTION", license_class="restricted")
    assert check(valid) == ([], [])


def test_open_license_list_accepts_cc_by_and_sa_but_not_nc_nd():
    assert {"MIT", "PostgreSQL", "CC0-1.0", "PSF-2.0"} <= ALLOWED_LICENSES
    assert all(is_open_license(x) for x in ("CC-BY-4.0", "CC-BY-SA-3.0", "CC-BY-2.5", "Apache-2.0"))
    assert not any(is_open_license(x) for x in ("CC-BY-NC-4.0", "CC-BY-ND-4.0", "NOASSERTION", "LicenseRef-X"))


def test_use_source_missing_license_evidence(check, valid):
    valid["license_quote"], valid["robots_checked"] = "", None
    only_error(check(valid), "license_quote", "robots_checked")


def test_excluded_source_needs_reason_and_cannot_have_use_pages(check, valid):
    valid["status"] = "excluded"
    errors, _ = check(valid)
    assert any("excluded_reason" in e for e in errors)
    assert sum("trang status use thuoc nguon status excluded" in e for e in errors) == 3  # moi trang use mot loi
    valid["excluded_reason"] = "robots.txt cam /guide/"
    for page in valid["pages"]:
        page["status"], page["excluded_reason"] = "excluded", "nguon bi loai"
    assert check(valid) == ([], [])
