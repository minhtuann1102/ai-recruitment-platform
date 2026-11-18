"""Trang tho -> ban ghi san sang ghi vao knowledge_chunks (spec 012, data-model §3).

Thu tu moi doan: chunk_page -> noise_reason -> clean_text + scrub_pii -> content_hash -> dedup -> ap quyet dinh soat
(khoa theo hash TRUOC khi ap). Ham thuan: khong doc / ghi file.
"""
import re
from typing import Any, Dict, List, Tuple

from . import settings
from .pii_patterns import scrub_pii
from .qa_record_builder import content_hash
from .text_cleaning import clean_text
from .textbook_chunker import chunk_page, render_content
from .textbook_manifest_models import Source, SourcePage, active_pages, dataset_name
from .textbook_noise_filter import noise_reason
from .textbook_review_decisions import Decisions, apply_decision

NOISE_REASONS = ("too_short", "code_only", "link_list", "blocked_heading")
STAT_KEYS = ("pages_in", "chunks", *NOISE_REASONS, "review_drop", "too_short_after_trim", "dedup", "unreviewed", "records")


_NUMBERING_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+")


def _heading_key(text: str) -> str:
    """So khop tieu de giua manifest va trang that: khong phan biet hoa thuong / khoang trang / so muc dau ("11. "),
    ky hieu headerlink cuoi tieu de (" ¶" cua Sphinx, " #" cua docs PostgreSQL) va ngoac kep cong / thang."""
    text = text.translate(_QUOTES).rstrip().rstrip("¶#").rstrip()
    return _NUMBERING_RE.sub("", " ".join(text.split())).casefold()


_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def _rows_page(page: Dict, row: SourcePage) -> Dict:
    """Trang chi gom section thuoc dong manifest: `sections` rong = ca trang; khong thi mot tieu de trong heading_path
    phai nam trong danh sach (cung URL co the co nhieu dong manifest voi `sections` khac nhau)."""
    if not row.sections:
        return page
    wanted = {_heading_key(name) for name in row.sections}
    # Khop o bat ky cap nao cua heading_path: trang mot file (vd Hibernate html_single) boc moi chuong duoi mot
    # tieu de chung ("Preface"), nen chi xet tieu de dau se khong khop chuong nao.
    kept = [s for s in page.get("sections", [])
            if any(_heading_key(h) in wanted for h in s.get("heading_path") or [])]
    return {**page, "sections": kept}


def _merge_tags(record: Dict, row: SourcePage) -> None:
    """Doan trung tu dong manifest khac: giu ban ghi dau nhung hop nhan track / tinh huong / topic (khong mat do phu)."""
    meta = record["metadata"]
    meta["tracks"] = sorted(set(meta["tracks"]) | set(row.tracks))
    meta["scenario_ids"] = sorted(set(meta["scenario_ids"]) | set(row.scenarios))
    meta["topic_ids"] = meta["topic_ids"] + [t for t in row.topics if t not in meta["topic_ids"]]


def _record(source: Source, row: SourcePage, title: str, heading_path: List[str], content: str,
            review: str, original_hash: str) -> Dict:
    metadata = {
        "dataset": dataset_name(source.source_id),
        "chunk_type": "doc_section",
        "source_id": source.source_id,
        "source_url": row.url,
        "license": source.license,
        "license_class": source.license_class,
        "attribution": source.attribution,
        "title": title,
        "heading_path": list(heading_path),
        "tracks": sorted(set(row.tracks)),
        "scenario_ids": sorted(set(row.scenarios)),
        "topic_ids": list(dict.fromkeys(row.topics)),  # giu thu tu manifest: topic_id = ma dau
    }
    if review:
        metadata["review"] = review
        if review == "trimmed":
            metadata["original_hash"] = original_hash
    return {
        "content": content,
        "content_hash": content_hash(content),
        "source_type": settings.TEXTBOOK_SOURCE_TYPE,
        "category": row.category,
        "difficulty": None,
        "topic_id": metadata["topic_ids"][0] if metadata["topic_ids"] else None,
        "language": source.language,
        "metadata": metadata,
    }


def build_records(source: Source, pages: List[Dict], decisions: Decisions) -> Tuple[List[Dict], Dict[str, Any]]:
    """(records, stats). Duyet dong manifest status use theo thu tu (de "giu doan dau" on dinh).

    ValueError tu apply_decision (trim khong khop) duoc nem len cho lenh bao loi. stats ngoai bo dem con:
    `section_misses` (dong manifest co `sections` nhung khong khop section nao: tieu de ghi sai) va `missing_urls`
    (URL status use khong co trong file tho: crawl thieu trang). Lenh process in canh bao / tu choi ghi theo hai danh sach nay.
    """
    stats: Dict[str, Any] = {key: 0 for key in STAT_KEYS}
    stats["section_misses"] = []
    stats["missing_urls"] = []
    pages_by_url = {p["url"]: p for p in pages}
    matched_urls = set()
    records: List[Dict] = []
    by_hash: Dict[str, Dict] = {}  # hash goc va hash sau trim -> ban ghi da giu
    for _, row in active_pages([source]):
        raw = pages_by_url.get(row.url)
        if raw is None:
            if row.url not in stats["missing_urls"]:
                stats["missing_urls"].append(row.url)
            continue
        matched_urls.add(row.url)
        row_page = _rows_page(raw, row)
        if row.sections and not row_page["sections"]:
            stats["section_misses"].append(f"{row.url} {row.sections}")
        for chunk in chunk_page(row_page):
            stats["chunks"] += 1
            heading_path, body = chunk["heading_path"], chunk["body"]
            reason = noise_reason(heading_path, body)
            if reason:
                stats[reason] += 1
                continue
            content = scrub_pii(clean_text(render_content(raw.get("title", ""), heading_path, body)))
            original = content_hash(content)
            if original in by_hash:
                stats["dedup"] += 1
                _merge_tags(by_hash[original], row)
                continue
            decision = decisions.decisions.get(original)
            review = ""
            if decision is None:
                stats["unreviewed"] += 1
            else:
                content, why = apply_decision(content, decision)
                if content is None:
                    stats["too_short_after_trim" if why == "too_short_after_trim" else "review_drop"] += 1
                    continue
                review = why  # "keep" | "trimmed"
                final = content_hash(content)
                if final in by_hash:  # hai doan khac nhau cat xong thanh cung noi dung (content_hash la khoa duy nhat)
                    stats["dedup"] += 1
                    _merge_tags(by_hash[final], row)
                    by_hash[original] = by_hash[final]
                    continue
            record = _record(source, row, raw.get("title", ""), heading_path, content, review, original)
            by_hash[original] = by_hash[record["content_hash"]] = record
            records.append(record)
    stats["pages_in"] = len(matched_urls)
    stats["records"] = len(records)
    return records, stats
