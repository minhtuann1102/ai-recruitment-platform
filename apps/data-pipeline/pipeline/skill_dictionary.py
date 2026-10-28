"""Danh muc ky nang JD (spec 009 research R5, FR-010): bi danh -> slug, khop ky nang trong van ban.

Nap data/seeds/skill_dictionary.yaml va kiem luat cua contract (slug duy nhat, chu thuong; bi danh khong trung giua
hai ky nang, so khop khong phan biet hoa thuong). Vi pham -> SkillDictionaryError (process-jd thoat 1).
slug va name cua moi ky nang cung la bi danh.
"""
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Pattern, Tuple

import yaml

from .settings import SKILL_DICTIONARY_PATH

GROUPS = ("backend", "frontend", "mobile_fullstack", "devops", "ai_data")  # thu tu = thu tu hoa cua group_of
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9+#.-]*$")
# Bi danh trung tu thuong ("go live", "the rest of", "spring 2026", "Chị C."): chi nhan khi la the ky nang
# (skills_raw), khong nhan khi gap trong tieu de / mo ta
TAG_ONLY_TERMS = frozenset({"c", "r", "go", "rest", "express", "spring", "swift"})


class SkillDictionaryError(ValueError):
    pass


def _key(term: str) -> str:
    return " ".join(unicodedata.normalize("NFC", term).lower().split())


@dataclass(frozen=True)
class Skill:
    slug: str
    name: str
    category: str
    group: str
    aliases: Tuple[str, ...]


def _parse_skill(index: int, entry: object) -> Skill:
    if not isinstance(entry, dict):
        raise SkillDictionaryError(f"muc {index}: phai la mapping")
    missing = [f for f in ("slug", "name", "category", "group") if not str(entry.get(f) or "").strip()]
    if missing:
        raise SkillDictionaryError(f"muc {index}: thieu {', '.join(missing)}")
    slug = str(entry["slug"]).strip()
    if not _SLUG_RE.match(slug):
        raise SkillDictionaryError(f"slug '{slug}' phai chu thuong, khong khoang trang")
    if entry["group"] not in GROUPS:
        raise SkillDictionaryError(f"slug '{slug}': group '{entry['group']}' khong thuoc {', '.join(GROUPS)}")
    aliases = entry.get("aliases") or []
    if not isinstance(aliases, list):
        raise SkillDictionaryError(f"slug '{slug}': aliases phai la danh sach")
    return Skill(slug, str(entry["name"]).strip(), str(entry["category"]).strip(), entry["group"],
                 tuple(str(a).strip() for a in aliases if str(a).strip()))


class SkillDictionary:
    def __init__(self, skills: Iterable[Skill]):
        self.skills: Dict[str, Skill] = {}
        self._alias_to_slug: Dict[str, str] = {}
        for skill in skills:
            if skill.slug in self.skills:
                raise SkillDictionaryError(f"slug trung: '{skill.slug}'")
            self.skills[skill.slug] = skill
            for term in dict.fromkeys(_key(t) for t in (skill.slug, skill.name, *skill.aliases)):
                owner = self._alias_to_slug.setdefault(term, skill.slug)
                if owner != skill.slug:
                    raise SkillDictionaryError(f"bi danh '{term}' trung giua '{owner}' va '{skill.slug}'")
        self._text_re = self._compile_text_pattern()

    def _compile_text_pattern(self) -> Optional[Pattern[str]]:
        # Dai truoc: "react native" thang "react", "asp.net" thang ".net", "node.js" thang "node"
        terms = sorted((t for t in self._alias_to_slug if t not in TAG_ONLY_TERMS), key=lambda t: (-len(t), t))
        if not terms:
            return None
        body = "|".join(r"\s+".join(re.escape(part) for part in t.split(" ")) for t in terms)
        # Ranh gioi: khong dinh chu / so; sau ky nang khong duoc la + hoac # ("c++" khong khop "c")
        return re.compile(rf"(?<![\w])(?:{body})(?![\w+#])", re.IGNORECASE)

    def canonical(self, name: str) -> Optional[str]:
        """Ten ky nang (the skills_raw) -> slug; ngoai danh muc -> None."""
        return self._alias_to_slug.get(_key(name))

    def resolve(self, names: Iterable[str]) -> Tuple[List[str], List[str]]:
        """(slug trong danh muc, ten ngoai danh muc), ca hai da sap va bo trung."""
        known, unknown = set(), {}
        for name in names:
            slug = self.canonical(name)
            if slug:
                known.add(slug)
            elif _key(name):
                unknown.setdefault(_key(name), " ".join(name.split()))
        return sorted(known), [unknown[k] for k in sorted(unknown)]

    def find_in_text(self, text: str) -> List[str]:
        """Slug cac ky nang xuat hien trong van ban (ranh gioi tu, khong phan biet hoa thuong), da sap."""
        if not text or self._text_re is None:
            return []
        text = unicodedata.normalize("NFC", text)
        return sorted({self._alias_to_slug[_key(m.group(0))] for m in self._text_re.finditer(text)})

    def group_of(self, slugs: Iterable[str]) -> Optional[str]:
        """Nhom xuat hien nhieu nhat; hoa thi theo thu tu GROUPS; khong co ky nang -> None."""
        counts = Counter(self.skills[s].group for s in slugs if s in self.skills)
        if not counts:
            return None
        return max(GROUPS, key=lambda g: (counts[g], -GROUPS.index(g)))

    def name_of(self, slug: str) -> str:
        return self.skills[slug].name if slug in self.skills else slug


def load_skill_dictionary(path: Path = SKILL_DICTIONARY_PATH) -> SkillDictionary:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SkillDictionaryError(f"khong doc duoc {path}: {exc}") from exc
    if not isinstance(data, list) or not data:
        raise SkillDictionaryError(f"{path}: phai la danh sach ky nang khong rong")
    return SkillDictionary(_parse_skill(i, entry) for i, entry in enumerate(data, 1))
