"""Chuan hoa truong JD (spec 009 research R6, FR-011): cap bac, loai hinh, ngon ngu (+ thanh pho tu jd_city).

Luong tach rieng o jd_salary.py, thanh pho o jd_city.py (file < 200 dong). Moi ham thuan (khong I/O), cung input -> cung output (FR-014).
"""
import re
import unicodedata
from typing import Iterable, List, Optional

from .jd_city import normalize_city  # noqa: F401  (giu API cu: jd_normalizer.normalize_city)

LEVELS = ("Intern", "Junior", "Mid", "Senior", "Lead", "Manager")
# Tu khoa cap bac trong tieu de; tieu de co nhieu tu khoa -> lay tu khoa xuat hien som nhat
_TITLE_LEVEL_RULES = (
    ("Intern", r"intern(?:ship)?|thực tập(?: sinh)?|trainee"),
    ("Junior", r"fresher|junior|jr\.?"),
    ("Mid", r"middle|mid(?:-level)?"),
    ("Senior", r"senior|sr\.?"),
    ("Lead", r"(?:tech |team )?lead(?:er)?|trưởng nhóm"),
    ("Manager", r"manager|quản lý|trưởng phòng|head of"),
)
_TITLE_LEVEL_RE = re.compile(
    "|".join(rf"(?P<{level}>(?<![\w])(?:{pattern})(?![\w]))" for level, pattern in _TITLE_LEVEL_RULES), re.IGNORECASE
)
_MONTHS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:months?|tháng)", re.IGNORECASE)
# Nguon ma experience_raw khong phai so nam that: itviec chi co 4 gia tri ("10 months", "37 months", "61 months",
# "No requirements") la nhom itviec tu gan, mo ta cung JD ghi 1-5 nam (Clarifications 2026-10-28)
UNRELIABLE_EXPERIENCE_SOURCES = frozenset({"itviec"})
MAX_DESCRIPTION_YEARS = 10  # "hon 20 nam kinh nghiem" trong mo ta thuong la cua cong ty, khong phai yeu cau
_RANGE = r"(\d+(?:[.,]\d+)?)\s*\+?\s*(?:(?:-|–|~|to|đến)\s*\d+\s*\+?\s*)?"
_DESCRIPTION_YEARS_RE = re.compile(
    rf"{_RANGE}(?:năm|years?|yrs?)\b[^.\n]{{0,25}}?(?:kinh nghiệm|experience)"
    rf"|(?:kinh nghiệm|experience)[^.\n\d]{{0,30}}?{_RANGE}(?:năm|years?|yrs?)\b",
    re.IGNORECASE,
)
_YEARS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*\+?\s*(?:-|–|to|đến)?\s*(?:\d+\s*)?(?:years?|yrs?|năm)", re.IGNORECASE)

_REMOTE_RE = re.compile(r"telecommute|remote|từ xa|work from home|wfh", re.IGNORECASE)
_HYBRID_RE = re.compile(r"hybrid", re.IGNORECASE)

# Ngon ngu theo ti le chu cai co dau tieng Viet / tong chu cai. JD tieng Viet thuan ~0.2-0.3,
# JD tieng Anh chi lan ten cong ty Viet < 0.03, JD song ngu nam giua
VI_RATIO_MIN = 0.12
EN_RATIO_MAX = 0.03


def level_from_title(title: str) -> Optional[str]:
    match = _TITLE_LEVEL_RE.search(unicodedata.normalize("NFC", title or ""))
    return match.lastgroup if match else None


def years_of_experience(experience_raw: Optional[str]) -> Optional[float]:
    """'36 months' -> 3.0; '2 năm', '3+ years', '1 - 3 years' -> so dau; '1 year 6 months' -> 1.5; khong co so -> None."""
    text = (experience_raw or "").strip()
    months, years = _MONTHS_RE.search(text), _YEARS_RE.search(text)
    if not (months or years):
        return None
    total = float(years.group(1).replace(",", ".")) if years else 0.0
    return total + (float(months.group(1).replace(",", ".")) / 12 if months else 0.0)


def years_from_description(description: Optional[str]) -> Optional[float]:
    """So nam dau tien di kem 'kinh nghiệm' / 'experience' trong mo ta ('3 năm kinh nghiệm', 'Experience: 2+ years',
    'at least 5 years of hands-on experience'); > MAX_DESCRIPTION_YEARS bi bo qua."""
    for match in _DESCRIPTION_YEARS_RE.finditer(unicodedata.normalize("NFC", description or "")):
        years = float((match.group(1) or match.group(2)).replace(",", "."))
        if years <= MAX_DESCRIPTION_YEARS:
            return years
    return None


def level_from_years(years: Optional[float]) -> Optional[str]:
    if years is None:
        return None
    if years < 3:  # duoi 12 thang = fresher, gop vao Junior; Intern chi tu tieu de (Clarifications 2026-10-28)
        return "Junior"
    return "Mid" if years < 5 else "Senior"


def normalize_level(title: str, experience_raw: Optional[str], description: Optional[str] = None,
                    source: str = "") -> Optional[str]:
    """Tu khoa tieu de -> so nam o experience_raw (tru nguon UNRELIABLE_EXPERIENCE_SOURCES) -> so nam trong mo ta;
    khong suy ra duoc -> None."""
    years = None if source in UNRELIABLE_EXPERIENCE_SOURCES else years_of_experience(experience_raw)
    if years is None:
        years = years_from_description(description)
    return level_from_title(title) or level_from_years(years)


def normalize_work_type(employment_types: Iterable[str], *texts: Optional[str]) -> str:
    """TELECOMMUTE / remote / tu xa -> remote; hybrid -> hybrid; con lai onsite."""
    haystack = " | ".join([*(employment_types or []), *(t for t in texts if t)])
    if _HYBRID_RE.search(haystack):
        return "hybrid"
    return "remote" if _REMOTE_RE.search(haystack) else "onsite"


def _is_vietnamese_letter(ch: str) -> bool:
    return ch in "đĐ" or (ch.isalpha() and any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", ch)))


def vietnamese_ratio(text: str) -> float:
    letters: List[str] = [ch for ch in unicodedata.normalize("NFC", text or "") if ch.isalpha()]
    return sum(map(_is_vietnamese_letter, letters)) / len(letters) if letters else 0.0


def detect_language(text: str) -> str:
    ratio = vietnamese_ratio(text)
    if ratio >= VI_RATIO_MIN:
        return "vi"
    return "en" if ratio <= EN_RATIO_MAX else "mixed"
