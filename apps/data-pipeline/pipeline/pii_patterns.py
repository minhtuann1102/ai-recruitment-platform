"""Phat hien / xoa thong tin ca nhan: email va so dien thoai (FR-005, FR-023, constitution V).

Khong tinh la PII: domain vi du theo RFC 2606 (example.com, *.test...) va dia chi SSH dang git@host
thuong gap trong Q&A DevOps.
"""
import re
from typing import List, Tuple

_EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b")
# VN: +84 / 0084 / 0 roi 9-10 chu so, cho phep dau cach / cham / gach giua cac so
_VN_PHONE_RE = re.compile(r"(?<![\w.+])(?:\+84|0084|0)(?:[ .-]?\d){9,10}(?![\w.])")
# Quoc te: bat buoc dau +, 8-15 chu so (co the co ngoac vung)
_INTL_PHONE_RE = re.compile(r"(?<![\w.])\+\d{1,3}(?:[ .-]?\(?\d+\)?){2,5}(?![\w.])")
_EXAMPLE_DOMAINS = ("example.com", "example.org", "example.net")
_EXAMPLE_TLDS = (".test", ".example", ".invalid", ".localhost")


def _is_example_email(local: str, domain: str) -> bool:
    domain = domain.lower()
    return (
        local.lower() == "git"
        or domain in _EXAMPLE_DOMAINS
        or domain.endswith(tuple("." + d for d in _EXAMPLE_DOMAINS))
        or domain.endswith(_EXAMPLE_TLDS)
    )


def _phone_digit_count(text: str) -> int:
    return sum(ch.isdigit() for ch in text)


def find_pii(text: str) -> List[Tuple[str, str]]:
    """Tra ve [(loai, chuoi khop)] voi loai la 'email' hoac 'phone'."""
    found = [
        ("email", m.group(0)) for m in _EMAIL_RE.finditer(text) if not _is_example_email(m.group(1), m.group(2))
    ]
    found += [("phone", m.group(0)) for m in _VN_PHONE_RE.finditer(text)]
    found += [
        ("phone", m.group(0))
        for m in _INTL_PHONE_RE.finditer(text)
        if 8 <= _phone_digit_count(m.group(0)) <= 15 and not m.group(0).startswith(("+84", "+0084"))
    ]
    return found


def scrub_pii(text: str) -> str:
    """Thay PII bang nhan [email] / [phone]; giu nguyen email vi du."""
    for kind, value in find_pii(text):
        text = text.replace(value, f"[{kind}]")
    return text
