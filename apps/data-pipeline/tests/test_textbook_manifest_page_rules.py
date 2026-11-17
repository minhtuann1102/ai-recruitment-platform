"""pipeline/textbook_manifest_rules: luat cap trang (URL, catalog, category, topic), truy van tinh huong va canh bao.

Fixture dung chung o tests/textbook_manifest_fixtures.py; luat cap nguon o test_textbook_source_manifest.
"""
import copy

from pipeline.textbook_source_manifest import validate_sources
from textbook_manifest_fixtures import SOURCES_FIXTURE, VALID_NAME, check, only_error, queries, tracks, valid  # noqa: F401


def test_duplicate_url_and_sections_pair_within_and_across_sources(check, valid):
    valid["pages"].append(copy.deepcopy(valid["pages"][0]))
    only_error(check(valid), "locking.html", "trung (URL, sections)", "valid-source.yaml")
    other = {**copy.deepcopy(valid), "source_id": "other", "pages": [copy.deepcopy(valid["pages"][0])]}
    valid["pages"].pop()
    errors, _ = check(valid, extra=("other", other))
    assert any("other.yaml" in e and "trung (URL, sections)" in e for e in errors)


def test_same_url_with_different_sections_is_not_duplicate(check, valid):
    page = copy.deepcopy(valid["pages"][2])
    page["sections"] = ["Other"]
    valid["pages"].append(page)
    assert check(valid)[0] == []


def test_url_must_share_host_with_homepage_except_markdown(check, valid):
    valid["pages"][0]["url"] = "https://elsewhere.example.com/guide/locking.html"
    only_error(check(valid), "elsewhere.example.com", "homepage")
    valid["format"] = "markdown"
    assert check(valid)[0] == []


def test_unknown_catalog_codes(check, valid):
    page = valid["pages"][0]
    page["tracks"], page["scenarios"], page["topics"] = ["be_track", "ghost_track"], ["scn.be.orders", "scn.ghost"], ["ghost.topic"]
    errors, _ = check(valid)
    assert any("track khong co trong catalog: ghost_track" in e for e in errors)
    assert any("scenario khong co trong catalog: scn.ghost" in e for e in errors)
    assert any("topic khong co trong catalog: ghost.topic" in e for e in errors)


def test_scenario_must_belong_to_a_listed_track(check, valid):
    valid["pages"][0]["tracks"] = ["fe_track"]
    errors, _ = check(valid)
    assert any("scn.be.orders thuoc track be_track" in e for e in errors)


def test_category_must_be_main_category_or_system_design(check, valid):
    valid["pages"][0]["category"] = "Frontend"
    only_error(check(valid), "locking.html", "category 'Frontend'", "System Design")
    valid["pages"][0]["category"] = "System Design"
    assert check(valid)[0] == []


def test_database_category_rejected_for_scenario_page(check, valid):
    valid["pages"][0]["category"] = "Database"  # scenario khong bao gio tim thay category nay (R2)
    only_error(check(valid), "locking.html", "category 'Database'")


def test_multi_track_page_with_different_main_categories_needs_system_design(check, valid):
    page = valid["pages"][0]
    page["tracks"], page["scenarios"] = ["be_track", "fe_track"], ["scn.be.orders", "scn.fe.dashboard"]
    only_error(check(valid), "category chinh khac nhau", "System Design")
    page["category"] = "System Design"
    assert check(valid)[0] == []


def test_topic_page_takes_category_of_first_topic(check, valid):
    page = valid["pages"][0]
    page["scenarios"], page["topics"], page["category"] = [], ["be.data.sql"], "Backend"
    only_error(check(valid), "category cua topic dau tien", "be.data.sql", "Database")
    page["category"] = "Database"  # US4: category cua topic, khong can la category chinh cua track
    assert check(valid)[0] == []


def test_page_needs_scenarios_or_topics(check, valid):
    valid["pages"][0]["scenarios"] = []
    only_error(check(valid), "locking.html", "scenarios lan topics")


def test_excluded_page_needs_reason(check, valid):
    valid["pages"][0]["status"] = "excluded"
    only_error(check(valid), "locking.html", "excluded_reason")


def test_unknown_query_key_and_missing_query_en_are_errors(check, valid):
    errors, _ = check(valid, query_override={"scn.ghost": {"query_en": "valid enough words here to pass the check ok"},
                                             "scn.be.orders": {"terms": ["a", "b", "c"]}})
    assert any("scn.ghost" in e and "catalog" in e for e in errors)
    assert any("scn.be.orders" in e and "query_en" in e for e in errors)


def test_warning_when_scenario_has_two_or_six_pages(check, valid):
    valid["pages"].pop()
    errors, warnings = check(valid)
    assert errors == [] and warnings == ["scn.be.orders (be_track): 2 trang status use (can 3-5, FR-003)"]
    for i in range(4):  # 2 + 4 = 6 hang trang
        page = copy.deepcopy(valid["pages"][0])
        page["url"] = f"https://docs.example.org/guide/extra-{i}.html"
        valid["pages"].append(page)
    assert "6 trang" in check(valid)[1][0]


def test_warning_when_track_has_no_official_source(check, valid):
    valid["kind"] = "supplementary"
    errors, warnings = check(valid)
    assert errors == [] and len(warnings) == 1 and "be_track" in warnings[0] and "official" in warnings[0]


def test_warning_when_scenario_has_no_query_row(check, valid):
    errors, warnings = check(valid, query_override={"scn.fe.dashboard": {"query_en": "dashboard state management with react hooks and context", "terms": ["a", "b", "c"]}})
    assert errors == [] and any("scn.be.orders" in w and "scenario-queries.yaml" in w for w in warnings)


def test_empty_manifest_has_no_errors_or_warnings(tracks):
    assert validate_sources([], tracks, {}) == ([], [])

