"""Kieu du lieu manifest nguon textbook (spec 012, contract textbook-source-manifest §1).

Chi chua dataclass, hang so va ham thuan nho; doc file nam o textbook_source_manifest, luat kiem o
textbook_manifest_rules.
"""
import re
from dataclasses import dataclass, field
from typing import Iterator, List, Tuple

from .settings import TEXTBOOK_DATASET_PREFIX

SCENARIO_QUERIES_FILE = "scenario-queries.yaml"  # nam cung thu muc voi manifest, khong phai mot nguon
SOURCE_ID_RE = re.compile(r"^[a-z0-9-]+$")
SOURCE_KINDS = ("official", "supplementary")
FORMATS = ("html", "markdown")
STATUSES = ("use", "excluded")
PAGE_KINDS = ("guide", "concept", "tutorial")  # khong nhan trang tham chieu API (FR-003)
LICENSE_CLASSES = ("open", "restricted")

# Danh sach mo (research R11): ma SPDX co dinh; CC-BY va CC-BY-SA moi phien ban khop bang CC_OPEN_RE
# (khong khop CC-BY-NC / CC-BY-ND)
ALLOWED_LICENSES = frozenset({"CC0-1.0", "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "PSF-2.0", "PostgreSQL"})
CC_OPEN_RE = re.compile(r"^CC-BY(?:-SA)?-\d+(?:\.\d+)?(?:-[A-Za-z]+)?$")


class ManifestError(RuntimeError):
    """File manifest khong doc duoc (YAML hong, sai kieu); loi noi dung manifest do validate_sources bao."""


def is_open_license(license_id: str) -> bool:
    return license_id in ALLOWED_LICENSES or bool(CC_OPEN_RE.match(license_id))


@dataclass
class SourcePage:
    url: str = ""
    category: str = ""
    tracks: List[str] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)  # chi US4
    sections: List[str] = field(default_factory=list)  # rong = ca trang
    kind: str = ""
    why: str = ""
    status: str = ""
    excluded_reason: str = ""

    @property
    def key(self) -> Tuple[str, Tuple[str, ...]]:
        """Khoa chong trung: cung URL voi sections khac nhau la hop le."""
        return self.url, tuple(sorted(self.sections))


@dataclass
class Source:
    file: str = ""  # ten file manifest, dung trong thong bao loi
    source_id: str = ""
    name: str = ""
    kind: str = ""
    homepage: str = ""
    format: str = ""
    content_selector: str = ""
    language: str = "en"
    license: str = ""
    license_class: str = ""
    license_url: str = ""
    license_quote: str = ""
    license_checked: str = ""
    robots_checked: str = ""
    robots_note: str = ""
    attribution: str = ""
    status: str = ""
    excluded_reason: str = ""
    pages: List[SourcePage] = field(default_factory=list)


def dataset_name(source_id: str) -> str:
    """metadata.dataset cua moi doan thuoc nguon nay (research R1)."""
    return f"{TEXTBOOK_DATASET_PREFIX}{source_id}"


def active_pages(sources: List[Source]) -> Iterator[Tuple[Source, SourcePage]]:
    """Trang status use cua nguon status use: dung de crawl, dem do phu va bang in ra."""
    for source in sources:
        if source.status != "use":
            continue
        for page in source.pages:
            if page.status == "use":
                yield source, page
