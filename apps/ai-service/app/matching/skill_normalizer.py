"""Chuan hoa ten ky nang CV -> slug theo danh muc cua 009 (spec 017 FR-009, research R6).

skill_dictionary.yaml la ban sao cua apps/data-pipeline/data/seeds/skill_dictionary.yaml (test ben pipeline giu hai
ban dong bo). Ky nang trong CV la dang the nen chi can anh xa ten -> slug (khoa NFC, chu thuong, gop khoang trang,
giong _key cua pipeline/skill_dictionary.py); khong can tim ky nang trong van ban tu do.
"""
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

DICTIONARY_PATH = Path(__file__).resolve().parent / "skill_dictionary.yaml"


def match_key(term: str) -> str:
    return " ".join(unicodedata.normalize("NFC", term).lower().split())


@dataclass(frozen=True)
class _Dictionary:
    alias_to_slug: Dict[str, str]
    slug_to_name: Dict[str, str]


@lru_cache(maxsize=1)
def _load() -> _Dictionary:
    entries = yaml.safe_load(DICTIONARY_PATH.read_text(encoding="utf-8"))
    alias_to_slug: Dict[str, str] = {}
    slug_to_name: Dict[str, str] = {}
    for entry in entries:
        slug, name = str(entry["slug"]).strip(), str(entry["name"]).strip()
        slug_to_name[slug] = name
        # slug va name cung la bi danh; 009 da dam bao bi danh khong trung giua hai ky nang
        for term in (slug, name, *(entry.get("aliases") or [])):
            alias_to_slug.setdefault(match_key(str(term)), slug)
    return _Dictionary(alias_to_slug, slug_to_name)


def normalize(names: Iterable[str]) -> Tuple[List[str], int]:
    """Ten ky nang -> (slug trong danh muc, da sap va bo trung; so ten ngoai danh muc, tinh theo khoa chuan hoa).
    Ten rong bi bo qua. Khong tra ten ngoai danh muc de khong lo du lieu CV tho."""
    alias_to_slug = _load().alias_to_slug
    known, unknown = set(), set()
    for name in names:
        key = match_key(name)
        if not key:
            continue
        slug = alias_to_slug.get(key)
        if slug:
            known.add(slug)
        else:
            unknown.add(key)
    return sorted(known), len(unknown)


def display_name(slug: str) -> str:
    """Ten hien thi cua slug; slug la (khong co trong danh muc) tra lai chinh slug."""
    return _load().slug_to_name.get(slug, slug)
