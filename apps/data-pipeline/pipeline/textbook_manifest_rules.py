"""Luat kiem manifest textbook (contracts/textbook-source-manifest.md §2, §3): ham thuan, tra danh sach thong bao.

Loi lam validate-textbook thoat 1; canh bao chi thanh loi khi --strict. Moi thong bao mo dau bang ten file
manifest (+ URL cua trang) hoac ma scn.* de nguoi sua tim ra dong sai.
"""
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlsplit

from .settings import SYSTEM_DESIGN_CATEGORY
from .textbook_catalog_tracks import Track
from .textbook_manifest_models import (
    FORMATS,
    LICENSE_CLASSES,
    PAGE_KINDS,
    SCENARIO_QUERIES_FILE,
    SOURCE_ID_RE,
    SOURCE_KINDS,
    STATUSES,
    Source,
    SourcePage,
    active_pages,
    is_open_license,
)

MIN_PAGES_PER_SCENARIO, MAX_PAGES_PER_SCENARIO = 3, 5  # FR-003
QUERY_WORDS = (6, 20)  # contract §3
QUERY_TERMS = (3, 6)

_REQUIRED = ("source_id", "name", "kind", "homepage", "format", "status")
_REQUIRED_WHEN_USE = (
    "license", "license_class", "license_url", "license_quote", "license_checked", "robots_checked", "attribution",
)


def _license_errors(source: Source) -> List[str]:
    """license_class phai khop danh sach mo (research R11)."""
    if not source.license:
        return []
    if source.license_class == "open" and not is_open_license(source.license):
        return [f"{source.file}: license_class open nhung license '{source.license}' ngoai danh sach mo (R11), dung restricted"]
    if source.license_class == "restricted" and is_open_license(source.license):
        return [f"{source.file}: license_class restricted nhung license '{source.license}' thuoc danh sach mo (R11), dung open"]
    return []


def _category_errors(where: str, page: SourcePage, tracks: Dict[str, Track], topic_categories: Dict[str, str]) -> List[str]:
    """Category cua trang: tinh huong chi thay category chinh cua track + System Design (R2); trang US4 theo topic."""
    errors: List[str] = []
    known = [tracks[t] for t in page.tracks if t in tracks]
    if page.scenarios and known:
        mains = {track.main_category for track in known}
        if len(mains) > 1 and page.category != SYSTEM_DESIGN_CATEGORY:
            errors.append(f"{where}: tracks co category chinh khac nhau {sorted(mains)} nen category phai la "
                          f"{SYSTEM_DESIGN_CATEGORY}, khong phai '{page.category}'")
        elif page.category != SYSTEM_DESIGN_CATEGORY and page.category not in mains:
            errors.append(f"{where}: category '{page.category}' phai la category chinh cua track {sorted(mains)} "
                          f"hoac {SYSTEM_DESIGN_CATEGORY}")
    if page.topics and page.topics[0] in topic_categories and page.category != topic_categories[page.topics[0]]:
        errors.append(f"{where}: category '{page.category}' phai bang category cua topic dau tien "
                      f"{page.topics[0]} ('{topic_categories[page.topics[0]]}')")
    return errors


def _page_errors(source: Source, page: SourcePage, tracks: Dict[str, Track], topic_categories: Dict[str, str],
                 scenario_track: Dict[str, str]) -> List[str]:
    where = f"{source.file} {page.url or '(trang thieu url)'}"
    errors = [f"{where}: thieu truong bat buoc '{name}'" for name in ("url", "category", "kind", "status") if not getattr(page, name)]
    if not page.tracks:
        errors.append(f"{where}: thieu truong bat buoc 'tracks'")
    if page.status == "use" and not page.why:
        errors.append(f"{where}: trang status use thieu 'why'")
    for name, allowed in (("kind", PAGE_KINDS), ("status", STATUSES)):
        value = getattr(page, name)
        if value and value not in allowed:
            errors.append(f"{where}: {name} '{value}' khong hop le (chon {' | '.join(allowed)})")
    if page.status == "excluded" and not page.excluded_reason:
        errors.append(f"{where}: trang status excluded thieu excluded_reason")
    if page.status == "use" and source.status == "excluded":
        errors.append(f"{where}: trang status use thuoc nguon status excluded")
    if page.url and source.homepage and source.format != "markdown":
        if urlsplit(page.url).netloc.lower() != urlsplit(source.homepage).netloc.lower():
            errors.append(f"{where}: URL khong cung host voi homepage {source.homepage}")
    for label, codes, known in (("track", page.tracks, tracks), ("scenario", page.scenarios, scenario_track),
                                ("topic", page.topics, topic_categories)):
        unknown = [code for code in codes if code not in known]
        if unknown:
            errors.append(f"{where}: {label} khong co trong catalog: {', '.join(unknown)}")
    for scn in page.scenarios:
        if scn in scenario_track and scenario_track[scn] not in page.tracks:
            errors.append(f"{where}: scenario {scn} thuoc track {scenario_track[scn]}, khong nam trong tracks {page.tracks}")
    if not page.scenarios and not page.topics:
        errors.append(f"{where}: trang khong co ca scenarios lan topics")
    if page.category:
        errors.extend(_category_errors(where, page, tracks, topic_categories))
    return errors


def source_errors(source: Source, tracks: Dict[str, Track]) -> List[str]:
    """Loi cua mot file nguon va cac trang cua no (contract §2, cac muc khong can doi chieu nguon khac)."""
    errors = [f"{source.file}: thieu truong bat buoc '{name}'" for name in _REQUIRED if not getattr(source, name)]
    if source.source_id and (source.source_id != Path(source.file).stem or not SOURCE_ID_RE.match(source.source_id)):
        errors.append(f"{source.file}: source_id '{source.source_id}' phai khop ten file va theo mau [a-z0-9-]+")
    for name, allowed in (("kind", SOURCE_KINDS), ("format", FORMATS), ("status", STATUSES), ("license_class", LICENSE_CLASSES)):
        value = getattr(source, name)
        if value and value not in allowed:
            errors.append(f"{source.file}: {name} '{value}' khong hop le (chon {' | '.join(allowed)})")
    errors.extend(_license_errors(source))
    if source.status == "use":
        missing = [name for name in _REQUIRED_WHEN_USE if not getattr(source, name)]
        if missing:
            errors.append(f"{source.file}: nguon status use thieu {', '.join(missing)}")
    if source.status == "excluded" and not source.excluded_reason:
        errors.append(f"{source.file}: nguon status excluded thieu excluded_reason (chi ly do truy cap, khong phai giay phep)")
    topic_categories = {topic: cat for track in tracks.values() for topic, cat in track.topic_categories.items()}
    scenario_track = {scn: track.track_id for track in tracks.values() for scn in track.scenario_ids}
    for page in source.pages:
        errors.extend(_page_errors(source, page, tracks, topic_categories, scenario_track))
    return errors


def duplicate_page_errors(sources: List[Source]) -> List[str]:
    """Cap (URL, sections) trung trong cung nguon hoac giua hai nguon; cung URL voi sections khac nhau la hop le."""
    seen: Dict[Tuple, str] = {}
    errors: List[str] = []
    for source in sources:
        for page in source.pages:
            if not page.url:
                continue
            if page.key in seen:
                errors.append(f"{source.file} {page.url}: trung (URL, sections) voi {seen[page.key]}")
            else:
                seen[page.key] = source.file
    return errors


def query_issues(queries: Dict[str, Dict], tracks: Dict[str, Track]) -> Tuple[List[str], List[str]]:
    """scenario-queries.yaml: khoa la ma scn.* trong catalog + co query_en (loi); do dai query / terms (canh bao)."""
    scenario_ids = {scn for track in tracks.values() for scn in track.scenario_ids}
    errors: List[str] = []
    warnings: List[str] = []
    for key, entry in queries.items():
        where = f"{SCENARIO_QUERIES_FILE} {key}"
        if key not in scenario_ids:
            errors.append(f"{where}: ma scenario khong co trong catalog")
        query = str(entry.get("query_en") or "").strip() if isinstance(entry, dict) else ""
        if not query:
            errors.append(f"{where}: thieu query_en")
            continue
        words = len(query.split())
        if not QUERY_WORDS[0] <= words <= QUERY_WORDS[1]:
            warnings.append(f"{where}: query_en co {words} tu (nen {QUERY_WORDS[0]}-{QUERY_WORDS[1]})")
        terms = entry.get("terms")
        count = len(terms) if isinstance(terms, list) else 0
        if not QUERY_TERMS[0] <= count <= QUERY_TERMS[1]:
            warnings.append(f"{where}: terms co {count} muc (nen {QUERY_TERMS[0]}-{QUERY_TERMS[1]})")
    return errors, warnings


def coverage_warnings(sources: List[Source], tracks: Dict[str, Track], queries: Dict[str, Dict]) -> List[str]:
    """Canh bao FR-002 / FR-003: chi xet track da co trang status use; dem hang trang, moi (URL, sections) mot hang."""
    pages = list(active_pages(sources))
    present = sorted({track_id for _, page in pages for track_id in page.tracks if track_id in tracks})
    warnings: List[str] = []
    for track_id in present:
        if not any(source.kind == "official" for source, page in pages if track_id in page.tracks):
            warnings.append(f"track {track_id}: chua co nguon kind official nao co trang cho track nay (FR-002)")
        for scn in tracks[track_id].scenario_ids:
            count = sum(1 for _, page in pages if scn in page.scenarios)
            if not MIN_PAGES_PER_SCENARIO <= count <= MAX_PAGES_PER_SCENARIO:
                warnings.append(f"{scn} ({track_id}): {count} trang status use (can {MIN_PAGES_PER_SCENARIO}-{MAX_PAGES_PER_SCENARIO}, FR-003)")
            if scn not in queries:
                warnings.append(f"{scn} ({track_id}): chua co dong trong {SCENARIO_QUERIES_FILE}")
    return warnings
