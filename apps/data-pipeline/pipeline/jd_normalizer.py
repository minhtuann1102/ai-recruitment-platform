"""Chuan hoa truong JD (spec 009 research R6, FR-011): cap bac, loai hinh, thanh pho, ngon ngu.

Luong tach rieng o jd_salary.py (file < 200 dong). Moi ham thuan (khong I/O), cung input -> cung output (FR-014).
"""
import re
import unicodedata
from typing import Iterable, List, Optional

from .text_cleaning import normalize_for_compare

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
_YEARS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*\+?\s*(?:-|–|to|đến)?\s*(?:\d+\s*)?(?:years?|yrs?|năm)", re.IGNORECASE)

_REMOTE_RE = re.compile(r"telecommute|remote|từ xa|work from home|wfh", re.IGNORECASE)
_HYBRID_RE = re.compile(r"hybrid", re.IGNORECASE)

# Ten chuan -> bi danh (da bo dau, chu thuong, bo dau cau nhu normalize_for_compare)
CITY_ALIASES = {
    "Hà Nội": ("ha noi", "hanoi", "hn"),
    "Hồ Chí Minh": ("ho chi minh", "hochiminh", "hcm", "tp hcm", "tphcm", "hcmc", "sai gon", "saigon"),
    "Đà Nẵng": ("da nang", "danang"),
    "Hải Phòng": ("hai phong", "haiphong"),
    "Cần Thơ": ("can tho", "cantho"),
    "Bình Dương": ("binh duong",),
    "Đồng Nai": ("dong nai", "bien hoa"),
    "Bắc Ninh": ("bac ninh",),
    "Huế": ("hue", "thua thien hue"),
    "Khánh Hòa": ("khanh hoa", "nha trang"),
    "Quy Nhơn": ("quy nhon", "binh dinh"),
}
_CITY_RE = re.compile(
    "|".join(rf"\b{re.escape(alias)}\b" for aliases in CITY_ALIASES.values() for alias in aliases)
)
_ALIAS_TO_CITY = {alias: city for city, aliases in CITY_ALIASES.items() for alias in aliases}

# Ngon ngu theo ti le chu cai co dau tieng Viet / tong chu cai. JD tieng Viet thuan ~0.2-0.3,
# JD tieng Anh chi lan ten cong ty Viet < 0.03, JD song ngu nam giua
VI_RATIO_MIN = 0.12
EN_RATIO_MAX = 0.03


def level_from_title(title: str) -> Optional[str]:
    match = _TITLE_LEVEL_RE.search(unicodedata.normalize("NFC", title or ""))
    return match.lastgroup if match else None


def years_of_experience(experience_raw: Optional[str]) -> Optional[float]:
    """'36 months' -> 3.0; '2 năm', '3+ years', '1 - 3 years' -> so dau; khong co so -> None."""
    text = (experience_raw or "").strip()
    months = _MONTHS_RE.search(text)
    if months:
        return float(months.group(1).replace(",", ".")) / 12
    years = _YEARS_RE.search(text)
    return float(years.group(1).replace(",", ".")) if years else None


def level_from_years(years: Optional[float]) -> Optional[str]:
    if years is None:
        return None
    if years < 1:
        return "Intern"
    if years < 3:
        return "Junior"
    return "Mid" if years < 5 else "Senior"


def normalize_level(title: str, experience_raw: Optional[str]) -> Optional[str]:
    """Tu khoa tieu de thang so nam kinh nghiem; khong suy ra duoc -> None."""
    return level_from_title(title) or level_from_years(years_of_experience(experience_raw))


def normalize_work_type(employment_types: Iterable[str], *texts: Optional[str]) -> str:
    """TELECOMMUTE / remote / tu xa -> remote; hybrid -> hybrid; con lai onsite."""
    haystack = " | ".join([*(employment_types or []), *(t for t in texts if t)])
    if _HYBRID_RE.search(haystack):
        return "hybrid"
    return "remote" if _REMOTE_RE.search(haystack) else "onsite"


def normalize_city(locations: Iterable[str]) -> Optional[str]:
    """Dia diem dau tien nhan ra duoc -> ten chuan; trong mot chuoi lay thanh pho xuat hien som nhat."""
    for location in locations or []:
        match = _CITY_RE.search(normalize_for_compare(location or ""))
        if match:
            return _ALIAS_TO_CITY[match.group(0)]
    return None


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
