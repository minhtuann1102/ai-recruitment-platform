"""Doc va kiem manifest nguon textbook (spec 012, contracts/textbook-source-manifest.md §1-§3, research R11).

load_sources / load_scenario_queries chi doc file (ham thuan ngoai I/O do); validate_sources la ham thuan tra
(errors, warnings), luat nam o textbook_manifest_rules. Import ten pho bien tu day.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .textbook_catalog_tracks import Track
from .textbook_manifest_models import (  # noqa: F401  (re-export cho cac lenh va test)
    ALLOWED_LICENSES,
    SCENARIO_QUERIES_FILE,
    ManifestError,
    Source,
    SourcePage,
    active_pages,
    dataset_name,
    is_open_license,
)
from .textbook_manifest_rules import coverage_warnings, duplicate_page_errors, query_issues, source_errors


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path.name}: YAML sai dinh dang: {exc}") from exc


def _text(value: Any) -> str:
    """Gia tri YAML -> chuoi; ngay (date) thanh ISO, None thanh rong."""
    return "" if value is None else str(value).strip()


def _str_list(file: str, key: str, value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ManifestError(f"{file}: truong '{key}' phai la danh sach")
    return [_text(item) for item in value]


def _load_page(file: str, raw: Any) -> SourcePage:
    if not isinstance(raw, dict):
        raise ManifestError(f"{file}: moi muc trong 'pages' phai la mapping")
    return SourcePage(
        url=_text(raw.get("url")),
        category=_text(raw.get("category")),
        tracks=_str_list(file, "tracks", raw.get("tracks")),
        scenarios=_str_list(file, "scenarios", raw.get("scenarios")),
        topics=_str_list(file, "topics", raw.get("topics")),
        sections=_str_list(file, "sections", raw.get("sections")),
        kind=_text(raw.get("kind")),
        why=_text(raw.get("why")),
        status=_text(raw.get("status")),
        excluded_reason=_text(raw.get("excluded_reason")),
    )


def _load_source(path: Path) -> Source:
    data = _read_yaml(path)
    if not isinstance(data, dict):
        raise ManifestError(f"{path.name}: goc file phai la mapping")
    raw_pages = data.get("pages")
    if raw_pages is not None and not isinstance(raw_pages, list):
        raise ManifestError(f"{path.name}: truong 'pages' phai la danh sach")
    scalar_fields = (
        "source_id", "name", "kind", "homepage", "format", "content_selector", "license", "license_class",
        "license_url", "license_quote", "license_checked", "robots_checked", "robots_note", "attribution",
        "status", "excluded_reason",
    )
    values = {name: _text(data.get(name)) for name in scalar_fields}
    values["language"] = _text(data.get("language")) or "en"
    return Source(file=path.name, pages=[_load_page(path.name, p) for p in raw_pages or []], **values)


def load_sources(directory: Path) -> List[Source]:
    """Moi *.yaml trong thu muc (tru scenario-queries.yaml) thanh mot Source, theo ten file; thu muc chua co -> []."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return [_load_source(p) for p in sorted(directory.glob("*.yaml")) if p.name != SCENARIO_QUERIES_FILE]


def load_scenario_queries(directory: Path) -> Dict[str, Dict]:
    """{scn.*: {query_en, terms}} tu scenario-queries.yaml; chua co file -> {}."""
    path = Path(directory) / SCENARIO_QUERIES_FILE
    if not path.is_file():
        return {}
    data = _read_yaml(path)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ManifestError(f"{SCENARIO_QUERIES_FILE}: goc file phai la mapping")
    return data


def validate_sources(
    sources: List[Source], tracks: Dict[str, Track], queries: Dict[str, Dict]
) -> Tuple[List[str], List[str]]:
    """(errors, warnings) theo contract §2; moi thong bao co ten file + URL hoac ma."""
    errors: List[str] = []
    for source in sources:
        errors.extend(source_errors(source, tracks))
    errors.extend(duplicate_page_errors(sources))
    query_errors, query_warnings = query_issues(queries, tracks)
    errors.extend(query_errors)
    return errors, coverage_warnings(sources, tracks, queries) + query_warnings
