"""Thanh pho cua JD (spec 009 research R6, FR-011; Clarifications 2026-10-28).

Thu tu: ten thanh pho trong location_raw -> ten thanh pho tren dong "Địa điểm:" / "Nơi làm việc:" / "Location:" cua
mo ta -> quan / huyen trong location_raw (careerviet chi ghi quan: "Quận Cầu Giấy", "Quận 3") -> quan tren dong dia diem.
So khop tren chuoi da bo dau, chu thuong (normalize_for_compare). Ham thuan, cung input -> cung output (FR-014).
"""
import re
from typing import Dict, Iterable, List, Optional, Tuple

from .text_cleaning import normalize_for_compare

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
# Quan / huyen chi thuoc mot trong 3 thanh pho lon (ten trung giua cac tinh thi khong dua vao)
DISTRICTS = {
    "Hà Nội": (
        "cau giay", "dong da", "ba dinh", "hoan kiem", "hai ba trung", "thanh xuan", "hoang mai", "long bien",
        "tay ho", "nam tu liem", "bac tu liem", "ha dong", "dong anh", "gia lam", "thanh tri", "hoai duc",
    ),
    "Hồ Chí Minh": (
        *(f"quan {n}" for n in range(1, 13)), "binh thanh", "phu nhuan", "tan binh", "tan phu", "go vap",
        "binh tan", "thu duc", "nha be", "cu chi", "hoc mon", "binh chanh",
    ),
    "Đà Nẵng": ("hai chau", "thanh khe", "son tra", "ngu hanh son", "lien chieu", "cam le"),
}
_LOCATION_LINE_RE = re.compile(r"^\s*(?:địa điểm(?: làm việc)?|nơi làm việc|location|work location)\s*:", re.IGNORECASE)


def _pattern(table: Dict[str, Tuple[str, ...]]) -> Tuple[re.Pattern, Dict[str, str]]:
    aliases = sorted((a for names in table.values() for a in names), key=lambda a: (-len(a), a))
    return (re.compile("|".join(rf"\b{re.escape(a)}\b" for a in aliases)),
            {alias: city for city, names in table.items() for alias in names})


_CITY_RE, _ALIAS_TO_CITY = _pattern(CITY_ALIASES)
_DISTRICT_RE, _DISTRICT_TO_CITY = _pattern(DISTRICTS)


def _first(texts: Iterable[str], pattern: re.Pattern, table: Dict[str, str]) -> Optional[str]:
    """Chuoi dau tien nhan ra duoc -> ten chuan; trong mot chuoi lay ten xuat hien som nhat."""
    for text in texts:
        match = pattern.search(normalize_for_compare(text or ""))
        if match:
            return table[match.group(0)]
    return None


def location_lines(description: Optional[str]) -> List[str]:
    return [line for line in (description or "").split("\n") if _LOCATION_LINE_RE.match(line)]


def normalize_city(locations: Iterable[str], description: Optional[str] = None) -> Optional[str]:
    locations = list(locations or [])
    lines = location_lines(description)
    return (_first(locations, _CITY_RE, _ALIAS_TO_CITY) or _first(lines, _CITY_RE, _ALIAS_TO_CITY)
            or _first(locations, _DISTRICT_RE, _DISTRICT_TO_CITY) or _first(lines, _DISTRICT_RE, _DISTRICT_TO_CITY))
