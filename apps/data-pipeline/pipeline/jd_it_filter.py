"""Loc JD nghe IT (spec 009 FR-028; Clarifications 2026-10-28).

Thu tu: tieu de ngoai pham vi (ban hang / tu van / giang day / hanh chinh / phien dich / kiem toan vien, BA / PO / PM /
Scrum Master) -> khong IT, du co tu khoa IT. Con lai IT khi: tieu de khop tu khoa nghe IT hoac >= 1 ky nang cu the,
hoac the skills_raw co >= 1 ky nang cu the, hoac mo ta khop >= 2 ky nang cu the. Ky nang chung chung (GENERIC_SKILLS:
"cơ sở dữ liệu", "bảo mật thông tin", "network", "QA/QC", "IT support", ...) hay gap o JD ngan hang / san xuat /
kinh doanh ("Network Expansion Associate") nen khong du tu minh; vai tro that co tu khoa rieng trong _IT_TITLE_RE.
"""
import re
from typing import Iterable, Sequence

from .text_cleaning import normalize_for_compare

MIN_DESCRIPTION_SKILLS = 2  # mo ta khop >= 2 ky nang cu the thi giu du tieu de chung chung
GENERIC_SKILLS = frozenset({
    "database", "information-security", "cloud-computing", "networking", "software-testing", "it-support",
    "it-infrastructure",
})
_IT_TITLE_RE = re.compile(
    r"(?<![\w])(?:developer|engineer|engineering|lập trình|programmer|tester|testing|qa|qc|kiểm thử|devops|data|"
    r"software|phần mềm|công nghệ thông tin|cntt|frontend|front-end|backend|back-end|fullstack|full-stack|"
    r"solution architect|software architect|system admin|sysadmin|it helpdesk|it support|ai|"
    r"kỹ sư (?:phần mềm|hệ thống|mạng|dữ liệu|cntt|an toàn|bảo mật|ai)|vận hành hệ thống|quản trị hệ thống|"
    r"security|an toàn thông tin|an ninh mạng|an ninh thông tin|bảo mật|pentest(?:er)?|network admin(?:istrator)?|"
    r"quản trị mạng|dba|quản trị cơ sở dữ liệu)(?![\w])",
    re.IGNORECASE,
)
_IT_WORD_RE = re.compile(r"(?<![\w])IT(?![\w])")  # "Nhân viên IT", "IT Staff": phan biet hoa thuong (khong khop "it")
# So tren tieu de da bo dau, chu thuong, bo dau cau (normalize_for_compare) de bat ca tieu de khong dau
# ("PHAN TICH NGHIEP VU"); "consultant" khong co: tieng Anh phan lon la vai tro ky thuat (security / data consultant)
_NON_IT_TITLE_RE = re.compile(
    r"\b(?:pre ?sales?|sales?|telesales|kinh doanh|ban hang|tu van|marketing|business development|account manager|"
    r"account executive|cham soc khach hang|customer service|giang vien|giao vien|lecturer|teacher|trainer|"
    r"hanh chinh|phien dich|interpreter|comtor|kiem toan vien|auditor|field service|"
    r"business analyst|phan tich nghiep vu|product owner|product manager|project manager|quan ly du an|"
    r"quan tri du an|scrum master)\b"
)
# Viet tat phan biet hoa thuong; "BA ĐÌNH" (quan) va "5 PM" (gio) khong tinh
_NON_IT_ABBR_RE = re.compile(r"(?<![\w])(?:BA(?!\s+(?:ĐÌNH|Đình|DINH|Dinh))|PO|(?<!\d )PM)(?![\w])")


def _specific(slugs: Iterable[str]) -> list:
    return [s for s in slugs if s not in GENERIC_SKILLS]


def is_out_of_scope_title(title: str) -> bool:
    return bool(_NON_IT_TITLE_RE.search(normalize_for_compare(title)) or _NON_IT_ABBR_RE.search(title))


def is_it_job(title: str, title_skills: Sequence[str], description_skills: Sequence[str],
              tag_skills: Sequence[str] = ()) -> bool:
    if is_out_of_scope_title(title):
        return False
    return (bool(_specific(title_skills)) or bool(_IT_TITLE_RE.search(title)) or bool(_IT_WORD_RE.search(title))
            or bool(_specific(tag_skills)) or len(_specific(description_skills)) >= MIN_DESCRIPTION_SKILLS)
