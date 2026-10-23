from crawlers.react_docs_crawler import LICENSE, normalize_url, parse_page
from pipeline.pii_patterns import find_pii

PAGE_URL = "https://react.dev/learn/thinking-in-react"


def _parse(fixtures_dir):
    html = (fixtures_dir / "react_docs" / "sample_page.html").read_text(encoding="utf-8")
    return parse_page(PAGE_URL, html)


def test_sections_follow_heading_path(fixtures_dir):
    record, _ = _parse(fixtures_dir)
    paths = [s["heading_path"] for s in record["sections"]]
    assert paths == [
        ["Thinking in React"],
        ["Thinking in React", "Step 1: Break the UI into a component hierarchy"],
        ["Thinking in React", "Step 1: Break the UI into a component hierarchy", "Pitfall"],
        ["Thinking in React", "Step 2: Build a static version"],
    ]  # "Empty heading" khong co noi dung -> bo
    assert record["title"] == "Thinking in React"
    assert record["url"] == PAGE_URL and record["crawled_at"] and record["license"] == LICENSE


def test_block_text_kept_once_and_code_fenced(fixtures_dir):
    record, _ = _parse(fixtures_dir)
    step1 = record["sections"][1]["text"]
    assert step1.count("use single responsibility") == 1  # p trong li khong lap lai
    assert "```\nfunction App() {\n  return <FilterableProductTable />;\n}\n```" in step1
    assert "Copy" not in step1  # nut giao dien bi loai


def test_email_and_phone_are_scrubbed(fixtures_dir):
    record, _ = _parse(fixtures_dir)
    all_text = " ".join(s["text"] for s in record["sections"])
    assert not find_pii(all_text)
    assert "[email]" in all_text and all_text.count("[phone]") == 2


def test_links_limited_to_learn_and_reference_react(fixtures_dir):
    _, links = _parse(fixtures_dir)
    assert links == [
        "https://react.dev/learn/describing-the-ui",
        "https://react.dev/learn/quick-start",
        "https://react.dev/learn/thinking-in-react",  # link #anchor tro ve chinh trang
        "https://react.dev/reference/react/useState",
    ]


def test_normalize_url_rejects_similar_prefix_and_other_hosts():
    assert normalize_url("/reference/react", PAGE_URL) == "https://react.dev/reference/react"
    assert normalize_url("/reference/react-dom", PAGE_URL) is None
    assert normalize_url("/learnx", PAGE_URL) is None
    assert normalize_url("https://legacy.reactjs.org/learn", PAGE_URL) is None
    assert normalize_url("../learn?x=1#y", PAGE_URL) == "https://react.dev/learn"
