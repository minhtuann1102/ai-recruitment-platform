"""T022: build_records (data-model §3) — cot / metadata, loc sections, dedup, PII, quyet dinh drop / trim / keep."""
import pytest

from pipeline.qa_record_builder import content_hash
from pipeline.textbook_manifest_models import Source, SourcePage
from pipeline.textbook_record_builder import build_records
from pipeline.textbook_review_decisions import Decisions
from textbook_command_fixtures import BASE, CONSTRAINTS, LOCKING, PROSE, SOURCE_ID, page

NO_DECISIONS = Decisions(source_id=SOURCE_ID)
ATTRIBUTION = "Example Backend Docs, Copyright Example Authors"


def row(url, sections=None, tracks=("be_track",), scenarios=("scn.be.orders",), topics=()):
    return SourcePage(url=url, category="Backend", tracks=list(tracks), scenarios=list(scenarios), topics=list(topics),
                      sections=list(sections or []), kind="guide", status="use")


def make_source(*rows):
    return Source(file="t.yaml", source_id=SOURCE_ID, name="Example", kind="official", homepage=BASE, format="html",
                  language="en", license="MIT", license_class="open", attribution=ATTRIBUTION, status="use",
                  pages=list(rows))


def test_record_has_all_columns_and_metadata_with_sorted_tags():
    source = make_source(row(LOCKING, tracks=("fe_track", "be_track"), scenarios=("scn.z", "scn.a"),
                             topics=("smp.b", "smp.a")))
    records, stats = build_records(source, [page(LOCKING, "Locking", (["Row locks"], PROSE))], NO_DECISIONS)
    assert len(records) == 1 and stats["records"] == 1 and stats["pages_in"] == 1
    rec = records[0]
    assert rec["source_type"] == "textbook" and rec["difficulty"] is None and rec["language"] == "en"
    assert rec["category"] == "Backend" and rec["topic_id"] == "smp.b"  # ma dau theo thu tu manifest
    assert rec["content"].startswith("Locking > Row locks\n\n")
    assert rec["content_hash"] == content_hash(rec["content"])
    meta = rec["metadata"]
    assert meta["dataset"] == "de_textbook_valid-source" and meta["chunk_type"] == "doc_section"
    assert meta["source_id"] == SOURCE_ID and meta["source_url"] == LOCKING and meta["title"] == "Locking"
    assert meta["license"] == "MIT" and meta["license_class"] == "open" and meta["attribution"] == ATTRIBUTION
    assert meta["heading_path"] == ["Row locks"]
    assert meta["tracks"] == ["be_track", "fe_track"] and meta["scenario_ids"] == ["scn.a", "scn.z"]
    assert meta["topic_ids"] == ["smp.b", "smp.a"]
    assert "review" not in meta and stats["unreviewed"] == 1  # chua soat: khong co khoa review


def test_sections_filter_keeps_only_listed_first_headings_and_skips_uncrawled_urls():
    source = make_source(row(LOCKING, sections=["Cache", "Queue"]), row(CONSTRAINTS))
    raw = page(LOCKING, "Locking", (["Row locks"], PROSE), (["Cache", "TTL"], PROSE), (["Queue"], PROSE), ([], PROSE))
    records, stats = build_records(source, [raw], NO_DECISIONS)  # CONSTRAINTS chua crawl
    assert [r["metadata"]["heading_path"] for r in records] == [["Cache", "TTL"], ["Queue"]]
    assert stats["chunks"] == 2 and stats["pages_in"] == 1
    assert stats["missing_urls"] == [CONSTRAINTS]  # H1: URL status use khong co trong file tho duoc liet ke (process tu choi ghi)


def test_same_paragraph_on_two_pages_gives_one_record_and_dedup_one():
    source = make_source(row(LOCKING), row(CONSTRAINTS))
    pages = [page(LOCKING, "Locking", (["Row locks"], PROSE)), page(CONSTRAINTS, "Locking", (["Row locks"], PROSE))]
    records, stats = build_records(source, pages, NO_DECISIONS)
    assert len(records) == 1 and stats["dedup"] == 1
    assert records[0]["metadata"]["source_url"] == LOCKING  # giu doan dau theo thu tu manifest


def test_same_url_on_two_rows_dedups_but_merges_tags():
    source = make_source(row(LOCKING), row(LOCKING, sections=["Cache"], tracks=("fe_track",), scenarios=("scn.fe.x",)))
    raw = page(LOCKING, "Locking", (["Row locks"], PROSE), (["Cache"], PROSE))
    records, stats = build_records(source, [raw], NO_DECISIONS)
    assert len(records) == 2 and stats["dedup"] == 1
    cache = next(r for r in records if r["metadata"]["heading_path"] == ["Cache"])
    assert cache["metadata"]["tracks"] == ["be_track", "fe_track"]
    assert cache["metadata"]["scenario_ids"] == ["scn.be.orders", "scn.fe.x"]


def test_email_is_scrubbed_and_noise_chunks_are_counted_by_reason():
    source = make_source(row(LOCKING))
    raw = page(LOCKING, "Locking",
               (["Contact"], PROSE + " Write to lienhe@congty-gia.vn for help."),
               (["Short"], "Too few words here."),
               (["See Also"], PROSE))
    records, stats = build_records(source, [raw], NO_DECISIONS)
    assert len(records) == 1 and "congty-gia" not in records[0]["content"] and "[email]" in records[0]["content"]
    assert stats["too_short"] == 1 and stats["blocked_heading"] == 1 and stats["chunks"] == 3


def _decided(source, raw, make_decisions):
    """Build lan 1 khong decisions de lay hash that, lan 2 voi decisions dung hash do (khong tinh tay)."""
    first, _ = build_records(source, [raw], NO_DECISIONS)
    return build_records(source, [raw], Decisions(SOURCE_ID, "2026-11-16", "tung", make_decisions(first)))


def test_drop_trim_keep_decisions_are_applied_by_original_hash():
    source = make_source(row(LOCKING))
    raw = page(LOCKING, "Locking", (["A"], PROSE), (["B"], PROSE + "\n\nEdit this page on GitHub"), (["C"], PROSE),
               (["D"], PROSE))
    records, stats = _decided(source, raw, lambda first: {
        first[0]["content_hash"]: {"verdict": "drop", "reason": "nav"},
        first[1]["content_hash"]: {"verdict": "trim", "remove": ["Edit this page on GitHub"]},
        first[2]["content_hash"]: {"verdict": "keep"},
    })
    assert [r["metadata"]["heading_path"] for r in records] == [["B"], ["C"], ["D"]]  # A bi drop
    assert stats["review_drop"] == 1 and stats["unreviewed"] == 1  # D chua co quyet dinh
    trimmed, kept, undecided = records
    assert trimmed["metadata"]["review"] == "trimmed" and "Edit this page" not in trimmed["content"]
    assert trimmed["content_hash"] == content_hash(trimmed["content"])
    assert trimmed["metadata"]["original_hash"] != trimmed["content_hash"]
    assert kept["metadata"]["review"] == "keep" and "original_hash" not in kept["metadata"]
    assert "review" not in undecided["metadata"]


def test_trim_leaving_too_few_words_counts_too_short_after_trim():
    source = make_source(row(LOCKING))
    raw = page(LOCKING, "Locking", (["A"], PROSE))
    first, _ = build_records(source, [raw], NO_DECISIONS)
    cut = PROSE[: PROSE.index("so the second writer")]
    records, stats = build_records(source, [raw], Decisions(SOURCE_ID, decisions={
        first[0]["content_hash"]: {"verdict": "trim", "remove": [PROSE.replace(cut, "", 1)]}}))
    assert records == [] and stats["too_short_after_trim"] == 1


def test_trim_string_not_in_passage_raises_value_error_with_hash():
    source = make_source(row(LOCKING))
    raw = page(LOCKING, "Locking", (["A"], PROSE))
    first, _ = build_records(source, [raw], NO_DECISIONS)
    bad = Decisions(SOURCE_ID, decisions={first[0]["content_hash"]: {"verdict": "trim", "remove": ["not there"]}})
    with pytest.raises(ValueError, match=first[0]["content_hash"]):
        build_records(source, [raw], bad)


def test_section_names_match_ignoring_case_spacing_and_leading_numbering_and_misses_are_reported():
    source = make_source(row(LOCKING, sections=["11.  Locking"]), row(CONSTRAINTS, sections=["Missing name"]))
    pages = [page(LOCKING, "Hibernate", (["11. locking"], PROSE), (["12. Fetching"], PROSE)),
             page(CONSTRAINTS, "Constraints", (["Unique"], PROSE))]
    records, stats = build_records(source, pages, NO_DECISIONS)
    assert [r["metadata"]["heading_path"] for r in records] == [["11. locking"]]
    assert stats["section_misses"] == [f"{CONSTRAINTS} ['Missing name']"]


def test_heading_key_ignores_headerlink_marks_and_curly_quotes():
    from pipeline.textbook_record_builder import _heading_key

    assert _heading_key("Using “atomic” ¶") == _heading_key('Using "atomic"')
    assert _heading_key("5.4. Constraints #") == _heading_key("Constraints")
