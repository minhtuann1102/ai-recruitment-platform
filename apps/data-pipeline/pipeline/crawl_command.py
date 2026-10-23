"""Lenh crawl react-docs (US5): crawler mau -> data/raw/react_docs/<UTC timestamp>.jsonl.

Offline voi DB / LLM, chi can mang. 0 record -> thoat 1 (FR-025). Noi dung KHONG commit (FR-024).
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

from crawlers.polite_fetcher import PoliteFetcher
from crawlers.react_docs_crawler import BASE_URL, crawl_react_docs

from .settings import RAW_DIR

REACT_DOCS_DIR = RAW_DIR / "react_docs"


def run_crawl(args: argparse.Namespace) -> int:
    if args.max_pages < 1 or args.delay < 0:
        print("[loi] --max-pages phai >= 1 va --delay >= 0", file=sys.stderr)
        return 1
    started = time.monotonic()
    fetcher = PoliteFetcher(BASE_URL, delay=args.delay, max_pages=args.max_pages, render=args.render)
    try:
        records = crawl_react_docs(fetcher)
    finally:
        fetcher.close()
    elapsed = time.monotonic() - started
    print(
        f"== {len(records)} record / {fetcher.pages_requested} trang da tai "
        f"(max {args.max_pages}, delay {fetcher.delay:g}s, robots bo qua {fetcher.skipped_by_robots}) "
        f"trong {elapsed:.1f}s"
    )
    if not records:
        print("[loi] crawl thu 0 record (doi cau truc HTML hoac bi chan?)", file=sys.stderr)  # FR-025
        return 1
    REACT_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out = REACT_DOCS_DIR / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    print(f"-> {out}")
    return 0
