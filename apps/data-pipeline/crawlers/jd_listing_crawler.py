"""Trang danh sach -> link chi tiet -> Raw JD cua mot nguon (spec 009 research R4, FR-004, FR-006, FR-009).

crawl_source duyet trang danh sach 1, 2, ... den khi het link moi / het luot / nguon bi chan. Id da co
(existing_ids) bi bo qua KHONG gui request. Moi chuoi trong record duoc xoa PII truoc khi tra (FR-009).
"""
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from pipeline.jd_pii import scrub_jd_pii

from .jd_page_parser import missing_required, parse_job_page
from .jd_sources import JdSource
from .polite_fetcher import PoliteFetcher

# Trang danh sach loi lien tiep (khong phai bi chan, khong phai robots cam): dung nguon thay vi duyet tiep vo han
MAX_LISTING_FAILURES = 3
# Khoa dinh danh / thoi diem: khong qua scrub (URL co the chua chuoi so giong SDT)
_UNSCRUBBED_KEYS = ("source", "source_job_id", "url", "crawled_at")


def extract_detail_links(html: str, page_url: str, source: JdSource) -> List[Tuple[str, str]]:
    """[(url chi tiet tuyet doi, bo query / #fragment; source_job_id)] theo thu tu xuat hien, bo trung id va link ngoai host."""
    found: Dict[str, str] = {}
    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        absolute = urljoin(page_url, anchor["href"])
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https") or not source.is_own_host(absolute):
            continue
        job_id = source.job_id(absolute) if source.detail_link_re.search(parts.path) else None
        if job_id and job_id not in found:
            found[job_id] = f"{parts.scheme}://{parts.netloc}{parts.path}"
    return [(url, job_id) for job_id, url in found.items()]


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_jd_pii(value)
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    return value


def scrub_record(record: Dict) -> Dict:
    return {key: value if key in _UNSCRUBBED_KEYS else _scrub(value) for key, value in record.items()}


def crawl_source(
    source: JdSource,
    fetcher: PoliteFetcher,
    existing_ids: Set[str],
    max_jobs: int,
    now: datetime,
    max_pages: Optional[int] = None,
    log: Callable[[str], None] = print,
) -> Tuple[List[Dict], Dict]:
    """(record moi, thong ke). max_jobs: toi da so trang chi tiet gui di; max_pages: toi da so trang danh sach.

    status: blocked (fetcher bi chan) > empty (khong co link nao, khong co record moi lan id da co, hoac trang chi
    tiet da tai khong trang nao co JobPosting) > ok. Chay lai ma moi id da co -> ok (skipped_existing > 0).
    """
    crawled_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stats: Dict[str, Any] = {
        "listing_pages": 0, "detail_pages": 0, "new_records": 0, "skipped_existing": 0,
        "errors": 0, "unusable": 0, "skipped_by_robots": 0, "delay": fetcher.delay, "status": "ok",
    }
    records: List[Dict] = []
    seen: Set[str] = set()  # id da gap trong lan chay nay, qua cac trang danh sach
    attempts = parsed = failures = page = 0

    def has_budget() -> bool:
        return attempts < max_jobs and not (fetcher.blocked or fetcher.exhausted)

    while not (fetcher.blocked or fetcher.exhausted) and (max_pages is None or page < max_pages):
        page += 1
        listing_url = source.listing_url(page)
        robots_before = fetcher.skipped_by_robots
        html = fetcher.fetch(listing_url)
        if html is None:
            if fetcher.skipped_by_robots > robots_before:
                break  # danh sach bi robots cam: khong co gi de duyet
            stats["errors"] += 1
            failures += 1
            if failures >= MAX_LISTING_FAILURES:
                break
            continue
        failures = 0
        stats["listing_pages"] += 1
        new_links = [(url, job_id) for url, job_id in extract_detail_links(html, listing_url, source) if job_id not in seen]
        if not new_links:
            break  # het danh sach
        seen.update(job_id for _, job_id in new_links)
        for url, job_id in new_links:
            if job_id in existing_ids:
                stats["skipped_existing"] += 1
                continue
            if not has_budget():
                break
            requests_before, robots_before = fetcher.pages_requested, fetcher.skipped_by_robots
            detail_html = fetcher.fetch(url)
            attempts += fetcher.pages_requested - requests_before
            if detail_html is None:
                if fetcher.skipped_by_robots == robots_before:  # robots cam khong tinh la loi
                    stats["errors"] += 1
                continue
            stats["detail_pages"] += 1
            record = parse_job_page(detail_html, source, url, crawled_at)
            if record is None:
                log(f"[bo qua] {url}: khong co JobPosting")
                stats["unusable"] += 1
                continue
            parsed += 1
            record = scrub_record(record)
            if missing_required(record):
                log(f"[bo qua] {url}: thieu truong bat buoc {', '.join(missing_required(record))}")
                stats["unusable"] += 1
                continue
            records.append(record)
            stats["new_records"] += 1
        if not has_budget():
            break

    stats["skipped_by_robots"] = fetcher.skipped_by_robots
    if fetcher.blocked:
        stats["status"] = "blocked"
    elif (stats["new_records"] == 0 and stats["skipped_existing"] == 0) or (stats["detail_pages"] and not parsed):
        stats["status"] = "empty"
    return records, stats
