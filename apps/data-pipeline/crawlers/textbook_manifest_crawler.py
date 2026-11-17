"""Crawl mot nguon textbook theo manifest (spec 012, research R4): chi tai URL co status "use", khong theo link.

crawl_source la ham thuan ngoai viec goi hai ham tai ben ngoai (de test bang fetcher gia, khong mang):
  - fetch_html(url) -> Optional[str]: PoliteFetcher.fetch (None khi loi / robots cam / bi chan)
  - fetch_markdown(repo, path) -> str: GithubRawClient.fetch (nem loi HTTP khi 404 -> tinh la fetch_failed)
Moi trang ra dict theo data-model §2: {source_id, url, title, sections, crawled_at}. Trang khong dung duoc vao
`skipped` {url: ly do}, lo khong dung lai.
"""
import re
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple, Union

from pipeline.textbook_manifest_models import Source, active_pages

from .docs_section_parser import parse_html_page, parse_markdown_page

FETCH_FAILED = "fetch_failed"
ROBOTS_DISALLOWED = "robots_disallowed"
EMPTY = "empty"

# github.com/<owner>/<repo>/blob/<ref>/<path> (dang trong manifest cho nguon markdown) va
# raw.githubusercontent.com/<owner>/<repo>[/refs/heads|tags]/<ref>/<path> (dang system-design-primer dung).
# GithubRawClient.fetch(repo, path) khong nhan ref nen ref bi bo (API tra nhanh mac dinh cua repo).
_BLOB_RE = re.compile(r"^https://github\.com/([^/]+/[^/]+)/blob/[^/]+/(.+)$")
_RAW_RE = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+/[^/]+)/(?:refs/(?:heads|tags)/)?[^/]+/(.+)$")

Now = Union[datetime, Callable[[], datetime]]


def github_target(url: str) -> Optional[Tuple[str, str]]:
    """(repo, path) cho GithubRawClient.fetch tu URL blob hoac raw; None neu khong nhan ra."""
    clean = url.split("#", 1)[0].split("?", 1)[0]
    match = _BLOB_RE.match(clean) or _RAW_RE.match(clean)
    return (match.group(1), match.group(2)) if match else None


def _iso_utc(now: Now) -> str:
    moment = now() if callable(now) else now
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _robots_skips(fetch_html: Callable) -> Optional[int]:
    """So lan fetcher da bo qua vi robots, neu fetch_html la method cua PoliteFetcher (co skipped_by_robots)."""
    return getattr(getattr(fetch_html, "__self__", None), "skipped_by_robots", None)


def _download(source: Source, url: str, fetch_html: Callable, fetch_markdown: Callable) -> Tuple[Optional[str], str]:
    """(noi dung, ly do loi); noi dung None thi ly do la fetch_failed hoac robots_disallowed."""
    try:
        if source.format == "markdown":
            target = github_target(url)
            if target is None:  # khong goi mang voi URL la
                return None, FETCH_FAILED
            body = fetch_markdown(*target)
            return body, FETCH_FAILED
        robots_before = _robots_skips(fetch_html)
        body = fetch_html(url)
        robots_after = _robots_skips(fetch_html)
        # fetch tra None chung cho moi loi; dem robots tang thi do la robots cam, khong phai loi mang
        if body is None and robots_before is not None and robots_after is not None and robots_after > robots_before:
            return None, ROBOTS_DISALLOWED
        return body, FETCH_FAILED
    except Exception:  # 404 / loi mang cua mot trang khong dung ca lo
        return None, FETCH_FAILED


def _parse(source: Source, body: str) -> Optional[Dict]:
    """{title, sections} hoac None neu trang rong sau khi tach."""
    if not body or not body.strip():
        return None
    if source.format == "markdown":
        parsed = parse_markdown_page(body)
        return parsed if parsed["sections"] else None
    return parse_html_page(body, source.content_selector or None)


def crawl_source(
    source: Source, fetch_html: Callable, fetch_markdown: Callable, now: Now
) -> Tuple[List[Dict], Dict[str, str]]:
    """Tai moi URL status use cua nguon dung mot lan (cung URL nhieu dong manifest vi khac sections: chi tai mot
    lan, loc sections la viec cua buoc xu ly). `now` la datetime hoac ham tra datetime (crawled_at moi trang)."""
    pages: List[Dict] = []
    skipped: Dict[str, str] = {}
    seen = set()
    for _, page in active_pages([source]):
        if page.url in seen:
            continue
        seen.add(page.url)
        body, failure = _download(source, page.url, fetch_html, fetch_markdown)
        if body is None:
            skipped[page.url] = failure
            continue
        parsed = _parse(source, body)
        if parsed is None:
            skipped[page.url] = EMPTY
            continue
        pages.append(
            {
                "source_id": source.source_id,
                "url": page.url,
                "title": parsed["title"],
                "sections": parsed["sections"],
                "crawled_at": _iso_utc(now),
            }
        )
    return pages, skipped
