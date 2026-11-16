"""validate-textbook (spec 012, contracts/pipeline-cli-textbook.md): kiem manifest nguon, offline, khong DB / key.

Luat kiem nam o textbook_manifest_rules. check_manifest la diem vao chung: moi lenh textbook khac goi no truoc
va dung voi ma 1 khi co loi. Doc thu muc manifest qua `settings` luc goi (khong chup luc import) de test doi duoc.
"""
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import settings
from .textbook_catalog_tracks import Track, load_tracks
from .textbook_source_manifest import (
    ManifestError,
    Source,
    active_pages,
    load_scenario_queries,
    load_sources,
    validate_sources,
)
from .topic_catalog_reader import CatalogError

EXIT_OK, EXIT_INPUT_ERROR = 0, 1


@dataclass
class ManifestCheck:
    sources: List[Source] = field(default_factory=list)
    tracks: Dict[str, Track] = field(default_factory=dict)
    queries: Dict[str, Dict] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def check_manifest(sources_dir: Optional[Path] = None) -> ManifestCheck:
    """Doc manifest + scenario-queries + catalog va kiem; ManifestError / CatalogError neu file khong doc duoc."""
    directory = Path(sources_dir) if sources_dir else settings.TEXTBOOK_SOURCES_DIR
    result = ManifestCheck(
        sources=load_sources(directory),
        tracks=load_tracks([settings.catalog_dir()]),
        queries=load_scenario_queries(directory),
    )
    result.errors, result.warnings = validate_sources(result.sources, result.tracks, result.queries)
    return result


def _track_lines(check: ManifestCheck) -> List[str]:
    pages = list(active_pages(check.sources))
    lines = ["== track x nguon chinh thuc x trang (status use)", f"{'track':<18}{'official':>9}{'trang':>7}"]
    for track_id in check.tracks:
        rows = [(source, page) for source, page in pages if track_id in page.tracks]
        official = {source.source_id for source, _ in rows if source.kind == "official"}
        lines.append(f"{track_id:<18}{len(official):>9}{len(rows):>7}")
    return lines


def _scenario_lines(check: ManifestCheck) -> List[str]:
    pages = list(active_pages(check.sources))
    lines = ["== tinh huong x trang (status use)", f"{'scenario':<42}{'track':<18}{'trang':>6}{'query':>7}"]
    for track in check.tracks.values():
        for scn in track.scenario_ids:
            count = sum(1 for _, page in pages if scn in page.scenarios)
            lines.append(f"{scn:<42}{track.track_id:<18}{count:>6}{'co' if scn in check.queries else '-':>7}")
    return lines


def _source_lines(check: ManifestCheck) -> List[str]:
    lines = ["== nguon x giay phep", f"{'source':<24}{'kind':<14}{'status':<10}{'license':<34}{'class':<12}{'trang':>6}"]
    for source in check.sources:
        used = sum(1 for page in source.pages if page.status == "use")
        lines.append(f"{source.source_id or source.file:<24}{source.kind:<14}{source.status:<10}"
                     f"{source.license or '-':<34}{source.license_class or '-':<12}{used:>6}")
    return lines


def run_validate_textbook(args: argparse.Namespace) -> int:
    strict = bool(getattr(args, "strict", False))
    try:
        check = check_manifest()
    except (ManifestError, CatalogError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    if not check.sources:
        print(f"chua co nguon nao trong {settings.TEXTBOOK_SOURCES_DIR}")
    else:
        for lines in (_track_lines(check), _scenario_lines(check), _source_lines(check)):
            print("\n".join(lines))
    for message in check.errors:
        print(f"[loi] {message}")
    for message in check.warnings:
        print(f"[canh bao] {message}")
    suffix = " (--strict: canh bao tinh la loi)" if strict and check.warnings else ""
    print(f"== {len(check.sources)} nguon, {len(check.errors)} loi, {len(check.warnings)} canh bao{suffix}")
    return EXIT_INPUT_ERROR if check.errors or (strict and check.warnings) else EXIT_OK
