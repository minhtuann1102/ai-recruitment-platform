"""crawl-textbook (spec 012, contracts/pipeline-cli-textbook.md): tai cac trang status use cua mot nguon -> JSONL tho.

Ghi `TEXTBOOK_RAW_DIR/<source_id>/<UTC>.jsonl` (moi dong mot trang, data-model §2). Ma thoat: 0 xong; 1 manifest loi /
0 trang ghi duoc; 4 host chan bot (khong ghi file de file do khong thanh "file tho moi nhat" cua process-textbook);
1 cung khi co trang bi bo (loi tai / robots cam / rong): file van ghi nhung thieu trang, process-textbook se tu choi
no -> crawl lai. Chan bot = HTML 3 lan 403/429 lien tiep, hoac GitHub API tra 403/429 (het han muc).
"""
import argparse
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Tuple

from crawlers.github_raw_client import GithubRawClient
from crawlers.polite_fetcher import PoliteFetcher
from crawlers.textbook_manifest_crawler import crawl_source

from . import settings
from .textbook_command_common import load_checked_manifest, select_sources
from .textbook_manifest_models import Source, active_pages
from .textbook_processed_io import write_jsonl

EXIT_OK, EXIT_INPUT_ERROR, EXIT_BLOCKED = 0, 1, 4
DEFAULT_MAX_PAGES = 60  # tran request cua PoliteFetcher; nang len khi manifest co nhieu URL hon

Fetchers = Tuple[Callable, Callable, Callable[[], bool], Callable[[], None]]


def _unused(*_args):
    raise RuntimeError("fetcher nay khong dung cho dinh dang cua nguon")


def make_fetchers(source: Source, delay: float, render: bool, page_count: int) -> Fetchers:
    """(fetch_html, fetch_markdown, is_blocked, close). fetch_html la method rang buoc cua PoliteFetcher de
    crawl_source phat hien robots; chi dung cai ma dinh dang nguon can (PoliteFetcher doc robots.txt ngay khi tao)."""
    if source.format == "markdown":
        client = GithubRawClient(delay=delay)
        return _unused, client.fetch, (lambda: client.blocked), client.close
    fetcher = PoliteFetcher(
        base_url=source.homepage, delay=delay, max_pages=max(DEFAULT_MAX_PAGES, page_count), render=render
    )
    return fetcher.fetch, _unused, (lambda: fetcher.blocked), fetcher.close


def _crawl_one(source: Source, delay: float, render: bool) -> int:
    page_count = len({page.url for _, page in active_pages([source])})
    started = time.monotonic()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # khong co ':' (Windows), sap theo ten = theo gio
    fetch_html, fetch_markdown, is_blocked, close = make_fetchers(source, delay, render, page_count)
    try:
        pages, skipped = crawl_source(source, fetch_html, fetch_markdown, lambda: datetime.now(timezone.utc))
        blocked = is_blocked()
    finally:
        close()
    print(f"== {source.source_id}: {page_count} trang trong manifest, {len(pages)} tai duoc, "
          f"{len(skipped)} bo, {time.monotonic() - started:.1f}s")
    for reason, count in sorted(Counter(skipped.values()).items()):
        print(f"   bo theo ly do {reason}: {count}")
    for url, reason in skipped.items():
        print(f"   [{reason}] {url}")
    if blocked:
        print(f"loi: {source.source_id} chan bot (3 lan 403/429 lien tiep), khong ghi file", file=sys.stderr)
        return EXIT_BLOCKED
    if not pages:
        print(f"loi: {source.source_id} khong tai duoc trang nao, khong ghi file", file=sys.stderr)
        return EXIT_INPUT_ERROR
    path = Path(settings.TEXTBOOK_RAW_DIR) / source.source_id / f"{stamp}.jsonl"
    write_jsonl(path, pages)  # nguyen tu (tmp roi replace): ghi do khong thanh "file tho moi nhat"
    print(f"   ghi {path}")
    if skipped:  # file thieu trang: process-textbook tu choi no cho toi khi crawl du
        print(f"loi: {source.source_id} thieu {len(skipped)}/{page_count} trang (liet ke o tren): crawl lai truoc khi "
              "process-textbook (file van ghi)", file=sys.stderr)
        return EXIT_INPUT_ERROR
    return EXIT_OK


def run_crawl_textbook(args: argparse.Namespace) -> int:
    check = load_checked_manifest()
    if check is None:
        return EXIT_INPUT_ERROR
    source_ids = getattr(args, "source", None) or []
    if not source_ids:
        print("loi: crawl-textbook can --source (khong crawl moi nguon mot luc)", file=sys.stderr)
        return EXIT_INPUT_ERROR
    sources = select_sources(check, source_ids)
    if sources is None:
        return EXIT_INPUT_ERROR
    delay, render = float(getattr(args, "delay", 1.0)), bool(getattr(args, "render", False))
    return max(_crawl_one(source, delay, render) for source in sources)
