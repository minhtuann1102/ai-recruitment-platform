"""Tach section JD + chunk offline (spec 009 research R7, FR-012).

Tieu de section la mot dong rieng (co the co gach dau dong, so thu tu, '#', dau ':' cuoi) khop nguyen dong voi mot
cum Viet / Anh duoi day; dong dai co chua "Yêu cầu ..." la noi dung, khong phai tieu de. Noi dung truoc tieu de dau
tien va JD khong nhan ra tieu de nao -> 'description'. Section 'summary' dung tu tieu de, cong ty, ky nang, cap bac.
"""
import hashlib
import re
import unicodedata
from typing import Dict, Iterable, List, Optional

from .collect_command import MAX_ANSWER_CHARS

SECTION_KEYS = ("summary", "description", "requirements", "responsibilities", "benefits")
_HEADINGS = {
    "description": (
        "mô tả công việc", "mô tả", "chi tiết công việc", "job description", "job descriptions", "description",
        "about the job", "about the role", "job overview", "the job", "giới thiệu công việc",
    ),
    "requirements": (
        "yêu cầu", "yêu cầu công việc", "yêu cầu ứng viên", "yêu cầu chung", "kỹ năng yêu cầu", "requirements",
        "job requirements", "requirement", "your skills", "your skills and experience", "your skills & experience",
        "qualifications", "skills and experience", "skills & experience", "what we are looking for",
        "what we're looking for",
    ),
    "responsibilities": (
        "trách nhiệm", "trách nhiệm công việc", "nhiệm vụ", "responsibilities", "job responsibilities",
        "your role", "your role and responsibilities", "your role & responsibilities", "what you will do",
        "what you'll do",
    ),
    "benefits": (
        "quyền lợi", "quyền lợi được hưởng", "phúc lợi", "chế độ đãi ngộ", "benefits", "why you'll love working here",
        "what we offer", "what we can offer", "perks", "perks and benefits", "perks & benefits",
    ),
}
_HEADING_TO_KEY = {phrase: key for key, phrases in _HEADINGS.items() for phrase in phrases}
# Gach dau dong, '#', so thu tu "1." / "I." / "1)" o dau dong; ':' va khoang trang o cuoi
_HEADING_PREFIX_RE = re.compile(r"^(?:[#*\-•·–—>\s]|(?:\d{1,2}|[ivx]{1,4})[.)](?=\s))+", re.IGNORECASE)
_HEADING_SUFFIX_RE = re.compile(r"[\s:：\-–—]+$")


def heading_key(line: str) -> Optional[str]:
    text = unicodedata.normalize("NFC", line).replace("’", "'").strip()
    text = _HEADING_SUFFIX_RE.sub("", _HEADING_PREFIX_RE.sub("", text))
    return _HEADING_TO_KEY.get(" ".join(text.lower().split()))


def split_sections(description: str) -> Dict[str, str]:
    """description_text -> {description | requirements | responsibilities | benefits: noi dung}; section rong bi bo."""
    parts: Dict[str, List[str]] = {}
    current = "description"
    for line in (description or "").split("\n"):
        key = heading_key(line) if line.strip() else None
        if key:
            current = key
            continue
        parts.setdefault(current, []).append(line)
    sections = {key: "\n".join(lines).strip() for key, lines in parts.items()}
    return {key: sections[key] for key in SECTION_KEYS if sections.get(key)}


def build_summary(title: str, company: str, skill_names: Iterable[str], level: Optional[str]) -> str:
    lines = [title, f"Công ty: {company}"]
    if level:
        lines.append(f"Cấp bậc: {level}")
    names = list(skill_names)
    if names:
        lines.append(f"Kỹ năng: {', '.join(names)}")
    return "\n".join(lines)


def _split_long_line(line: str, limit: int) -> List[str]:
    """Dong dai hon limit: cat o khoang trang cuoi cung truoc limit (khong co thi cat cung), khong mat ky tu."""
    pieces = []
    while len(line) > limit:
        cut = line.rfind(" ", 1, limit + 1)
        cut = cut if cut > 0 else limit
        pieces.append(line[:cut])
        line = line[cut:]
    return pieces + [line]


def split_text(text: str, limit: int = MAX_ANSWER_CHARS) -> List[str]:
    """Chia theo doan (dong) sao cho moi phan <= limit; '\\n'.join(ket qua) == text khi khong co dong nao > limit."""
    if len(text) <= limit:
        return [text]
    pieces: List[str] = []
    current: List[str] = []
    size = 0
    for line in text.split("\n"):
        for part in _split_long_line(line, limit):
            extra = len(part) + (1 if current else 0)
            if current and size + extra > limit:
                pieces.append("\n".join(current))
                current, size = [], 0
                extra = len(part)
            current.append(part)
            size += extra
    if current:
        pieces.append("\n".join(current))
    return pieces


def chunk_hash(content: str) -> str:
    """Hash noi dung da chuan hoa (NFC, chu thuong, gop khoang trang): khoa dedup chunk (FR-013)."""
    normalized = " ".join(unicodedata.normalize("NFC", content).lower().split())
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_chunks(jd: Dict) -> List[Dict]:
    """1 chunk summary + 1 chunk moi section (section dai chia nhieu chunk), dung truong contract JD Chunk."""
    chunks = []
    for section in SECTION_KEYS:
        text = jd["sections"].get(section)
        for content in split_text(text) if text else []:
            chunks.append({
                "jd_id": jd["jd_id"],
                "section": section,
                "content": content,
                "content_hash": chunk_hash(content),
                "skills": list(jd["skills"]),
                "company": jd["company"],
                "language": jd["language"],
                "source_url": jd["source_url"],
            })
    return chunks
