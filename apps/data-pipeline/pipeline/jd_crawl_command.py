"""Lenh crawl-jd (spec 009 US1, contracts/pipeline-cli-jd.md): moi nguon -> data/raw/jd/<nguon>/<UTC ts>.jsonl.

Offline voi DB / LLM, chi can mang. Ma thoat: 4 co nguon bi chan (cac nguon con lai van chay het); 1 co nguon
empty, chay loi, hoac > 50% trang chi tiet da tai khong dung duoc (FR-006); con lai 0. Chay lai ma moi id da
co la thoat 0. Noi dung crawl KHONG commit (FR-007).
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

import httpx

from crawlers.jd_listing_crawler import crawl_source
from crawlers.jd_sources import SOURCES, JdSource
from crawlers.polite_fetcher import PoliteFetcher

from .settings import JD_RAW_DIR

EXIT_OK = 0
EXIT_EMPTY_OR_BROKEN = 1
EXIT_SOURCE_BLOCKED = 4
MAX_UNUSABLE_RATIO = 0.5  # qua nguong nay trang chi tiet da tai khong dung duoc -> lenh that bai


def load_existing_ids(source_name: str) -> Set[str]:
    """source_job_id da co trong cac file raw cu cua nguon: khong request lai (FR-006)."""
    ids: Set[str] = set()
    for path in sorted((JD_RAW_DIR / source_name).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                ids.add(str(json.loads(line)["source_job_id"]))
            except (ValueError, KeyError, TypeError):
                continue  # dong hong khong lam hong ca lan chay
    return ids


def write_raw(source_name: str, records: List[Dict], now: datetime) -> Path:
    out_dir = JD_RAW_DIR / source_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{now:%Y%m%dT%H%M%SZ}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return out


def print_summary(name: str, stats: Dict) -> None:
    print(f"== {name}")
    print(f"  trang danh sách đã tải: {stats['listing_pages']}")
    print(f"  trang chi tiết đã tải: {stats['detail_pages']}")
    print(f"  record mới: {stats['new_records']}")
    print(f"  id đã có, bỏ qua: {stats['skipped_existing']}")
    print(f"  lỗi: {stats['errors']}")
    print(f"  không dùng được (không có JobPosting / thiếu trường bắt buộc): {stats['unusable']}")
    print(f"  bỏ qua theo robots: {stats['skipped_by_robots']}")
    print(f"  delay: {stats['delay']:g}s")
    print(f"  trạng thái: {stats['status']}")


def _crawl_one(
    source: JdSource,
    args: argparse.Namespace,
    transport: Optional[httpx.BaseTransport],
    clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> Dict:
    now = datetime.now(timezone.utc)
    # Fetcher moi moi lan chay: robots doc lai, khong cache qua ngay. Luot = trang danh sach + trang chi tiet
    fetcher = PoliteFetcher(
        source.base_url,
        delay=args.delay,
        max_pages=args.max_pages + args.max_jobs,
        transport=transport,
        clock=clock,
        sleep=sleep,
    )
    try:
        records, stats = crawl_source(
            source, fetcher, load_existing_ids(source.name), args.max_jobs, now, max_pages=args.max_pages
        )
    finally:
        fetcher.close()
    print_summary(source.name, stats)
    if records:
        print(f"  -> {write_raw(source.name, records, now)}")
    return stats


def too_many_unusable(stats: Dict) -> bool:
    return bool(stats["detail_pages"]) and stats["unusable"] / stats["detail_pages"] > MAX_UNUSABLE_RATIO


def run_crawl_jd(
    args: argparse.Namespace,
    transport: Optional[httpx.BaseTransport] = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    if args.max_pages < 1 or args.max_jobs < 1 or args.delay < 0:
        print("[loi] --max-pages, --max-jobs phai >= 1 va --delay >= 0", file=sys.stderr)
        return EXIT_EMPTY_OR_BROKEN
    blocked, failed = [], []
    for name in dict.fromkeys(args.source or SOURCES):  # mac dinh ca 4 nguon; bo trung neu --source lap lai
        try:
            stats = _crawl_one(SOURCES[name], args, transport, clock, sleep)
        except Exception as exc:  # mot nguon loi khong dung cac nguon sau
            print(f"== {name}\n  [loi] {exc}", file=sys.stderr)
            failed.append(name)
            continue
        if stats["status"] == "blocked":
            blocked.append(name)
        elif stats["status"] == "empty" or too_many_unusable(stats):
            failed.append(name)
    if blocked:
        print(f"[loi] nguon bi chan, da dung: {', '.join(blocked)}", file=sys.stderr)
    if failed:
        print(f"[loi] nguon rong / loi / thieu truong hang loat: {', '.join(failed)}", file=sys.stderr)
    if blocked:
        return EXIT_SOURCE_BLOCKED
    return EXIT_EMPTY_OR_BROKEN if failed else EXIT_OK
