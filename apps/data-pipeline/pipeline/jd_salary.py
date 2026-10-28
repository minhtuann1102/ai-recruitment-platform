"""Chuan hoa luong JD (spec 009 research R6, FR-018): chi nhan so that, chu -> trong.

Thu tu: so trong salary_raw (min / max cua baseSalary, co the chi co min) -> salary_raw.text dang so
("9.000.000 VND - 20.000.000 VND", "15 - 25 triệu", "$1,000 - 2,000", "Up to 2000$") -> tieu de ("... Up to 60M").
Chu ("You'll love it", "Cạnh tranh", "Negotiable", "Thỏa thuận", "Sign in to view") -> (None, None, None).
salary_currency (VND | USD) chi co khi co salary_min hoac salary_max.
"""
import re
import unicodedata
from typing import Dict, Optional, Tuple

Salary = Tuple[Optional[int], Optional[int], Optional[str]]
NO_SALARY: Salary = (None, None, None)
CURRENCIES = ("VND", "USD")
USD_MAX = 100_000  # so luong < nguong ma khong ghi tien te -> USD, con lai VND

# Dau phan nghin VN / EN: nhom sau dau du 3 chu so ("15.000.000", "1,500"); con lai la so thap phan ("1.5")
_NUM = r"\d{1,3}(?:[.,]\d{3})+(?![\d])|\d+(?:[.,]\d+)?"
_UNIT = r"triệu|million|tr\b|m\b|k\b|usd|vnd|vnđ|đ\b|₫|\$"
_SALARY_RE = re.compile(
    rf"(?P<prefix>up\s*to|lên\s+(?:tới|đến)|tới|đến|max|from|từ|trên|over|min)?\s*(?P<cur1>\$|usd)?\s*"
    rf"(?P<a>{_NUM})\s*(?P<unit1>{_UNIT})?"
    rf"(?:\s*(?:-|–|~|to|đến)\s*(?P<cur2>\$|usd)?\s*(?P<b>{_NUM})\s*(?P<unit2>{_UNIT})?)?"
    rf"(?:(?<=k)\s*(?P<cur3>usd|vnd|vnđ|\$))?",  # tien te sau don vi k: "1.5k - 2k USD"
    re.IGNORECASE,
)
VND_MIN = 1_000_000  # luong VND duoi 1 trieu / thang la doc sai (vd "500k" khong ghi tien te), bo
_MAX_ONLY = ("up", "lên", "tới", "đến", "max")
_MILLION_UNITS = ("triệu", "million", "tr", "m")
_THOUSANDS_SEP_RE = re.compile(r"\d{1,3}(?:([.,])\d{3})(?:\1\d{3})*")


def _to_number(text: str) -> float:
    if _THOUSANDS_SEP_RE.fullmatch(text):
        return float(re.sub(r"[.,]", "", text))
    return float(text.replace(",", "."))


def _currency_for(values, explicit: Optional[str]) -> str:
    if explicit in CURRENCIES:
        return explicit
    return "USD" if max(values) < USD_MAX else "VND"


def _finish(low: Optional[float], high: Optional[float], currency: Optional[str]) -> Salary:
    values = [v for v in (low, high) if v is not None and v > 0]
    if not values:
        return NO_SALARY
    low, high = (int(v) if v is not None and v > 0 else None for v in (low, high))
    if low is not None and high is not None and low > high:
        low, high = high, low
    currency = _currency_for(values, currency)
    if currency == "VND" and max(values) < VND_MIN:
        return NO_SALARY
    return low, high, currency


def _from_match(match: re.Match) -> Optional[Salary]:
    units = [u.lower() for u in (match["cur1"], match["unit1"], match["cur2"], match["unit2"], match["cur3"]) if u]
    numbers = [_to_number(match[k]) for k in ("a", "b") if match[k]]
    if not units and max(numbers) < 1_000_000:  # so tran khong don vi ("Java 8", "5 years") khong phai luong
        return None
    if any(u in _MILLION_UNITS for u in units):
        numbers = [n * 1_000_000 if n < 1000 else n for n in numbers]
    elif "k" in units:
        numbers = [n * 1000 if n < USD_MAX else n for n in numbers]
    # Chi co don vi "k" -> chua ro tien te, de _currency_for doan theo do lon
    currency = "USD" if any(u in ("$", "usd") for u in units) else ("VND" if set(units) - {"k"} else None)
    if len(numbers) == 2:
        return _finish(numbers[0], numbers[1], currency)
    prefix = (match["prefix"] or "").lower()
    if prefix.startswith(_MAX_ONLY):
        return _finish(None, numbers[0], currency)
    if prefix:  # tu / from / tren / over / min
        return _finish(numbers[0], None, currency)
    return _finish(numbers[0], numbers[0], currency)


def parse_salary_text(text: Optional[str]) -> Salary:
    text = unicodedata.normalize("NFC", text or "")
    for match in _SALARY_RE.finditer(text):
        salary = _from_match(match)
        if salary and salary != NO_SALARY:
            return salary
    return NO_SALARY


def _number(value: object) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value > 0 else None


def normalize_salary(salary_raw: Optional[Dict], title: str = "") -> Salary:
    raw = salary_raw if isinstance(salary_raw, dict) else {}
    low, high = _number(raw.get("min")), _number(raw.get("max"))
    if low is not None or high is not None:
        currency = str(raw.get("currency") or "").strip().upper() or None
        return _finish(low, high, currency)
    from_text = parse_salary_text(raw.get("text") if isinstance(raw.get("text"), str) else None)
    return from_text if from_text != NO_SALARY else parse_salary_text(title)
