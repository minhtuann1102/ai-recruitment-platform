"""crawlers/docs_section_parser: vung noi dung theo selector, heading_path khong gom ten trang, markdown co khoi code."""
from bs4 import BeautifulSoup

from crawlers.docs_section_parser import content_root, parse_html_page, parse_markdown_page
from pipeline.pii_patterns import find_pii


def _read(fixtures_dir, name):
    return (fixtures_dir / "textbook" / name).read_text(encoding="utf-8")


def test_selector_takes_content_region_and_drops_sidebar_and_footer(fixtures_dir):
    page = parse_html_page(_read(fixtures_dir, "guide_page.html"), "#docContent")
    all_text = " ".join(s["text"] for s in page["sections"])
    assert "Documentation menu entry" not in all_text and "Footer text" not in all_text
    assert "Copy" not in all_text  # nut giao dien bi loai
    assert page["title"] == "Explicit Locking"


def test_heading_path_nests_h2_h3_and_excludes_page_title(fixtures_dir):
    page = parse_html_page(_read(fixtures_dir, "guide_page.html"), "#docContent")
    assert [s["heading_path"] for s in page["sections"]] == [
        [],  # doan mo dau duoi h1: path rong
        ["Row-Level Locks"],
        ["Row-Level Locks", "FOR UPDATE"],
        ["Deadlocks"],
    ]


def test_code_block_keeps_fence_and_pii_is_scrubbed(fixtures_dir):
    page = parse_html_page(_read(fixtures_dir, "guide_page.html"), "#docContent")
    for_update = page["sections"][2]["text"]
    assert "```\nSELECT * FROM stock WHERE sku = 'A1' FOR UPDATE;\n```" in for_update
    assert not find_pii(for_update) and "[email]" in for_update


def test_no_selector_uses_article_then_main(fixtures_dir):
    page = parse_html_page(_read(fixtures_dir, "article_only_page.html"), None)
    assert [s["heading_path"] for s in page["sections"]] == [["First Topic"]]
    assert "Sidebar" not in page["sections"][0]["text"]
    soup = BeautifulSoup("<html><body><main><p>x</p></main></body></html>", "html.parser")
    assert content_root(soup, "").name == "main"  # selector rong = chua khai


def test_unmatched_selector_gives_none_not_fallback(fixtures_dir):
    # selector sai phai lo ra thanh 0 section, khong am tham lay article / sidebar
    assert parse_html_page(_read(fixtures_dir, "article_only_page.html"), "#wrong") is None
    assert parse_html_page("<html><body><p>no headings here</p></body></html>", None) is None


def test_markdown_sections_use_hash_levels_without_title(fixtures_dir):
    page = parse_markdown_page(_read(fixtures_dir, "readme.md"))
    assert page["title"] == "The Sample Primer"
    assert [s["heading_path"] for s in page["sections"]] == [[], ["Cache"], ["Cache", "Cache-aside"], ["Asynchronism"]]


def test_markdown_hash_inside_code_block_is_not_a_heading(fixtures_dir):
    page = parse_markdown_page(_read(fixtures_dir, "readme.md"))
    aside = page["sections"][2]["text"]
    assert "```python\n# this hash line is a comment inside a code block, not a heading\n## neither is this one\n" in aside
    assert "value = cache.get(key)\n```" in aside
    assert "After the code block the explanation continues here." in aside
    assert "#### Fourth level heading stays in the body" in aside  # cap 4 khong tach
    assert len(page["sections"]) == 4  # hai dong '#' trong khoi code khong sinh section


def test_markdown_without_h1_has_empty_title_and_keeps_paths():
    page = parse_markdown_page("## Only H2\n\nBody text of the only section.\n\n### Child\n\nChild text.\n")
    assert page["title"] == ""
    assert [s["heading_path"] for s in page["sections"]] == [["Only H2"], ["Only H2", "Child"]]


def test_markdown_closing_hashes_stripped_but_c_sharp_kept():
    page = parse_markdown_page("# Title\n\n## Notes on C#\n\nSome text.\n\n## Closed heading ##\n\nOther text.\n")
    assert [s["heading_path"] for s in page["sections"]] == [["Notes on C#"], ["Closed heading"]]
