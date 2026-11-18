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


def test_markdown_without_h1_uses_front_matter_title_and_keeps_h2_siblings():
    text = "---\ntitle: Cache-aside pattern\nweight: 3\n---\nIntro text.\n\n## First\nAlpha body.\n\n### Deep\nDeep body.\n\n## Second\nBeta body.\n"
    page = parse_markdown_page(text)
    assert page["title"] == "Cache-aside pattern"
    assert [s["heading_path"] for s in page["sections"]] == [["First"], ["First", "Deep"], ["Second"]]
    assert all("weight" not in s["text"] for s in page["sections"])


def test_markdown_h1_wins_over_front_matter_and_unclosed_front_matter_is_text():
    page = parse_markdown_page("---\ntitle: Meta\n---\n# Real Title\n## A\nbody a\n")
    assert page["title"] == "Real Title" and page["sections"][0]["heading_path"] == ["A"]
    assert parse_markdown_page("---\ntitle: x\n## A\nbody\n")["title"] == ""


def _page(body, selector=None):
    return parse_html_page(f"<html><body><article>{body}</article></body></html>", selector)


def test_definition_list_terms_and_descriptions_are_kept():
    page = _page("<h1>Fetch</h1><h2>Options</h2><dl><dt>method</dt><dd>HTTP verb to use.</dd><dt>headers</dt><dd>Request headers.</dd></dl>")
    text = page["sections"][0]["text"]
    assert page["sections"][0]["heading_path"] == ["Options"]
    assert "method" in text and "HTTP verb to use." in text and "headers" in text


def test_hidden_elements_are_dropped_from_title_headings_and_chunks():
    page = _page(
        '<h1>Learn CSS<devsite-actions hidden data-nosnippet><devsite-feature-tooltip class="nocontent">'
        '<span slot="popout-heading">Stay organized with collections</span></devsite-feature-tooltip></devsite-actions>'
        '<div class="devsite-actions">Class form actions</div>'
        '<span hidden>Save collection</span><i aria-hidden="true">icon</i></h1>'
        '<p>Intro text.</p>'
        '<h2>Box model <a aria-hidden="TRUE" href="#box">#</a></h2><p>Body.<span hidden>secret <b>nested</b></span></p>'
    )
    assert page["title"] == "Learn CSS"
    assert [s["heading_path"] for s in page["sections"]] == [[], ["Box model"]]
    everything = " ".join(s["text"] for s in page["sections"]) + page["title"]
    for junk in ("organized", "Class form", "Save collection", "icon", "secret", "nested"):
        assert junk not in everything


def test_permalink_anchors_are_dropped_from_headings_and_definitions():
    page = _page(
        '<h1>Tasks<a class="headerlink" href="#tasks" title="Link to this heading">¶</a></h1><p>Intro.</p>'
        '<h2>Retrying<a class="headerlink" href="#retrying">&para;</a></h2>'
        '<dl><dt>Task.retry()<a class="headerlink" href="#retry" title="Link to this definition">¶</a></dt>'
        '<dd>Re-execute the task.</dd></dl>'
        '<h2>Locks <a href="#locks" class="id_link">#</a></h2><p>Row locks.</p>'
        '<h2>C# <a href="#cs">#</a></h2><p>Plain anchors stay.</p>'
    )
    assert page["title"] == "Tasks"
    assert [s["heading_path"] for s in page["sections"]] == [[], ["Retrying"], ["Locks"], ["C# #"]]
    assert "¶" not in " ".join(s["text"] for s in page["sections"])


def test_hidden_elements_outside_content_root_h1_fallback_are_dropped_too():
    html = ('<html><body><h1>Site <span hidden>hidden bit</span>Guide</h1>'
            '<main><h2>Part</h2><p>Text.</p></main></body></html>')
    assert parse_html_page(html, None)["title"] == "Site Guide"


def test_code_block_with_per_line_divs_keeps_line_breaks_and_indent():
    code = (
        '<pre><code>'
        '<div class="cm-line"><span>function</span> <span>f</span>() {<br/></div>'
        '<div class="cm-line">  <span>return</span> 1;<br/></div>'
        '<div class="cm-line"><br/></div>'
        '<div class="cm-line">}<br/></div>'
        '</code></pre>'
    )
    page = _page(f"<h1>T</h1><h2>Code</h2><p>Before.</p>{code}")
    assert "```\nfunction f() {\n  return 1;\n\n}\n```" in page["sections"][0]["text"]


def test_code_block_with_lines_without_br_and_plain_newline_block():
    divs = '<pre><code><div>first</div><div>second</div><div>third</div></code></pre>'
    plain = "<pre><code>alpha\nbeta\ngamma\n</code></pre>"
    page = _page(f"<h1>T</h1><h2>A</h2>{divs}<h2>B</h2>{plain}")
    assert "```\nfirst\nsecond\nthird\n```" in page["sections"][0]["text"]
    assert "```\nalpha\nbeta\ngamma\n```" in page["sections"][1]["text"]  # khong sinh dong trong thua


def test_html_without_h1_keeps_h2_as_siblings():
    page = _page("<h2>First</h2><p>Alpha.</p><h3>Deep</h3><p>Deep text.</p><h2>Second</h2><p>Beta.</p>")
    assert [s["heading_path"] for s in page["sections"]] == [["First"], ["First", "Deep"], ["Second"]]


def test_html_skipped_level_does_not_nest_sibling_h3():
    page = _page("<h1>T</h1><h3>One</h3><p>a</p><h3>Two</h3><p>b</p><h2>Mid</h2><p>c</p>")
    assert [s["heading_path"] for s in page["sections"]] == [["One"], ["Two"], ["Mid"]]


def test_definition_list_with_block_children_keeps_blocks_and_code_fence():
    # dang MDN: dd chua p / ul / pre va dl long; dd la container, khong nuot cac block con
    page = _page(
        "<h1>T</h1><h2>Options</h2><dl><dt><code>opt</code></dt>"
        "<dd><p>desc</p><ul><li>a</li></ul><pre>x = 1\ny = 2</pre>"
        "<dl><dt>inner</dt><dd>leaf</dd></dl></dd></dl>"
    )
    text = page["sections"][0]["text"]
    assert text.index("opt") < text.index("desc") < text.index("inner") < text.index("leaf")
    assert "desc\n\na\n\n```\nx = 1\ny = 2\n```" in text  # desc va a la hai block rieng, code giu fence


