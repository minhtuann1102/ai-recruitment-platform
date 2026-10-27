"""Xoa PII cua JD theo pham vi FR-009 (research R4): rong hon pii_patterns cua 005.

Ba loai: (1) email + so dien thoai (scrub_pii cua 005); (2) dong lien he cua nguoi tuyen dung;
(3) URL ho so ca nhan. scrub_jd_pii xoa ca ba; count_jd_pii dem ca ba (nguon cua pii_remaining), = 0 sau scrub.
Ten cong ty va URL cong ty (congty-gia.vn/careers) la du lieu to chuc, giu nguyen.
"""
import re
import unicodedata

from .pii_patterns import find_pii, scrub_pii

# Dong bat dau bang tu khoa lien he; chi la dong lien he khi kem SDT / email, hoac dung ten nguoi
# ngay sau tu khoa ("Contact us to learn more" khong kem gi -> giu)
_CONTACT_KEYWORD_RE = re.compile(
    r"^(?:người\s+liên\s+hệ|nguoi\s+lien\s+he|liên\s+hệ|lien\s+he|contact|hotline)\b", re.I
)
# Xung ho + ten: "Mr./Ms./Mrs./Anh/Chi" (dau cham tuy chon), "A./C." (bat buoc dau cham, tranh "A Bachelor ...")
_HONORIFIC_RE = re.compile(r"^(?:(?:Mr|Ms|Mrs|Anh|Chị)\b\.?|[AC]\.)\s+(\w+)")
_LEADING_MARK_RE = re.compile(r"^[\s\-*•·–—>]+")
_KEYWORD_TAIL_RE = re.compile(r"^[\s:：\-–—]*")
_PROFILE_URL_RE = re.compile(
    r"(?<![\w-])(?:https?://)?(?:[\w-]+\.)*(?:linkedin\.com/in/|facebook\.com/|fb\.com/|zalo\.me/|t\.me/)"
    r"(?:[^\s<>\"')\]]*[^\s<>\"')\].,;:!?])?",
    re.I,
)
PROFILE_URL_LABEL = "[link]"


def _is_name_after(text: str) -> bool:
    """Xung ho + ten viet hoa ("Chị Lan"), khong phai tu thuong ("anh em")."""
    match = _HONORIFIC_RE.match(text)
    return bool(match) and match.group(1)[:1].isupper()


def is_contact_line(line: str) -> bool:
    text = _LEADING_MARK_RE.sub("", unicodedata.normalize("NFC", line))
    if not text:
        return False
    has_contact_data = bool(find_pii(text))
    keyword = _CONTACT_KEYWORD_RE.match(text)
    if keyword:
        return has_contact_data or _is_name_after(_KEYWORD_TAIL_RE.sub("", text[keyword.end():]))
    return has_contact_data and _is_name_after(text)


def scrub_jd_pii(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    kept = "\n".join(line for line in text.split("\n") if not is_contact_line(line))
    # URL truoc scrub_pii: "zalo.me/0912345678" se thanh "zalo.me/[phone]" va de sot ky tu neu doi thu tu
    return scrub_pii(_PROFILE_URL_RE.sub(PROFILE_URL_LABEL, kept))


def count_jd_pii(text: str) -> int:
    text = unicodedata.normalize("NFC", text)
    contact_lines = sum(is_contact_line(line) for line in text.split("\n"))
    return len(find_pii(text)) + contact_lines + len(_PROFILE_URL_RE.findall(text))
