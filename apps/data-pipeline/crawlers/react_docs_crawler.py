"""Crawler mau US5: react.dev (/learn, /reference/react), noi dung CC BY 4.0 (research R8).

Moi trang -> 1 record thô {url, title, sections[{heading_path, text}], crawled_at, license}.
Text tach theo h1/h2/h3 trong <article> (fallback <main>); code block giu dang ``` de chuyen the Q&A sau.
Lam sach + scrub PII truoc khi luu (FR-023). Output data/raw/react_docs/ nam ngoai git (FR-024).
"""
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from pipeline.pii_patterns import scrub_pii
from pipeline.text_cleaning import clean_text

from .polite_fetcher import PoliteFetcher

BASE_URL = "https://react.dev"
START_URLS = ("https://react.dev/learn", "https://react.dev/reference/react")
ALLOWED_PREFIXES = ("/learn", "/reference/react")
LICENSE = "CC-BY-4.0"
HEADING_LEVELS = {"h1": 1, "h2": 2, "h3": 3}
BLOCK_TAGS = ("h1", "h2", "h3", "p", "li", "pre", "blockquote", "td", "th")
# Phan giao dien, khong phai noi dung (nut copy code, icon, script)
NOISE_TAGS = ("script", "style", "noscript", "svg", "button", "nav", "iframe")


def normalize_url(href: str, page_url: str) -> Optional[str]:
    """URL tuyet doi, bo #fragment / ?query / '/' cuoi; None neu ngoai react.dev hoac ngoai hai tien to."""
    parts = urlsplit(urljoin(page_url, href))
    if parts.scheme not in ("http", "https") or parts.netloc != urlsplit(BASE_URL).netloc:
        return None
    path = parts.path.rstrip("/") or "/"
    if not any(path == p or path.startswith(p + "/") for p in ALLOWED_PREFIXES):
        return None
    return f"{BASE_URL}{path}"


def _block_text(element: Tag) -> str:
    if element.name == "pre":
        code = element.get_text().strip("\n")
        return f"```\n{code}\n```" if code.strip() else ""
    return element.get_text(" ", strip=True)


def _content_root(soup: BeautifulSoup) -> Optional[Tag]:
    return soup.find("article") or soup.find("main") or soup.body


def parse_sections(root: Tag) -> List[Dict]:
    """Gom block theo heading gan nhat; heading_path = [h1, h2, h3] hien hanh. Bo section rong."""
    sections: List[Dict] = []
    path: List[str] = []
    buffer: List[str] = []

    def flush() -> None:
        text = scrub_pii(clean_text("\n\n".join(b for b in buffer if b)))
        if text and path:
            sections.append({"heading_path": list(path), "text": text})
        buffer.clear()

    for element in root.find_all(BLOCK_TAGS):
        # Block long trong block khac (p trong li, li trong li...) da nam trong text cua block ngoai
        if element.find_parent(BLOCK_TAGS) is not None:
            continue
        level = HEADING_LEVELS.get(element.name)
        if level is None:
            buffer.append(_block_text(element))
            continue
        flush()
        heading = scrub_pii(clean_text(element.get_text(" ", strip=True)))
        path[:] = path[: level - 1] + [heading]
    flush()
    return sections


def parse_page(url: str, html: str) -> Tuple[Optional[Dict], List[str]]:
    """(record hoac None neu trang khong co noi dung, cac link hop le de crawl tiep)."""
    soup = BeautifulSoup(html, "html.parser")
    links = sorted({u for a in soup.find_all("a", href=True) if (u := normalize_url(a["href"], url))})
    for noise in soup.find_all(NOISE_TAGS):
        noise.decompose()
    root = _content_root(soup)
    if root is None:
        return None, links
    sections = parse_sections(root)
    if not sections:
        return None, links
    h1 = root.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else url)
    record = {
        "url": url,
        "title": scrub_pii(clean_text(title.removesuffix(" – React"))),
        "sections": sections,
        "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "license": LICENSE,
    }
    return record, links


def crawl_react_docs(fetcher: PoliteFetcher) -> List[Dict]:
    """BFS tu START_URLS theo link cung domain duoi hai tien to; dung khi fetcher het luot."""
    queue = deque(START_URLS)
    seen = set(START_URLS)
    records: List[Dict] = []
    while queue and not fetcher.exhausted:
        url = queue.popleft()
        html = fetcher.fetch(url)
        if html is None:
            continue
        record, links = parse_page(url, html)
        if record is not None:
            records.append(record)
        for link in links:
            if link not in seen:
                seen.add(link)
                queue.append(link)
    return records
