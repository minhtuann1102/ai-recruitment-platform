"""Van ban embed cua CV va tap ky nang CV cho goi y viec lam (spec 017 FR-001, FR-009, research R4).

Khac app/cv_text.py (trich xuat va lam sach text tho cua file CV). O day dau vao la CvProfile da phan tich.
Van ban embed KHONG co danh sach ky nang (de cosine khong lap lai skill_match) va khong co tech, highlights, hoc van.
"""
from typing import Iterable, List, Tuple

from ..models_cv import CvProfile
from .skill_normalizer import normalize

MAX_EMBED_CHARS = 1200  # ~300-400 token: chi phi embed moi request nho (R4)
_SEP = " — "


def _line(*parts: str) -> str:
    """Noi cac phan khong rong bang dau gach; phan rong bi bo (khong co 'name —  — summary')."""
    return _SEP.join(p.strip() for p in parts if p and p.strip())


def build_cv_text(cv: CvProfile) -> str:
    """headline, moi kinh nghiem (role — summary), moi du an (name — role — summary); cat con MAX_EMBED_CHARS."""
    lines = [_line(cv.headline)]
    lines += [_line(e.role, e.summary) for e in cv.experiences]
    lines += [_line(p.name, p.role, p.summary) for p in cv.projects]
    return "\n".join(line for line in lines if line)[:MAX_EMBED_CHARS].rstrip()


def _dedup(names: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(n for n in names if n))


def cv_skill_names(cv: CvProfile) -> List[str]:
    """Ten tho: skills[].name, roi experiences[].tech, roi projects[].tech; giu thu tu, bo trung y het."""
    names = [s.name for s in cv.skills]
    names += [t for e in cv.experiences for t in e.tech]
    names += [t for p in cv.projects for t in p.tech]
    return _dedup(names)


def cv_skills(cv: CvProfile) -> Tuple[List[str], int]:
    """(slug ky nang CV, so ky nang ngoai danh muc) sau khi chuan hoa qua danh muc 009."""
    return normalize(cv_skill_names(cv))
