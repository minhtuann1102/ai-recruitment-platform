"""Loc nhieu tu dong cho doan giao trinh (spec 012, research R7), chay truoc buoc soat cua worker.

`noise_reason` kiem theo thu tu co dinh: blocked_heading -> code_only -> link_list -> too_short; tra ly do dau tien
khop (thong ke theo ly do phu thuoc thu tu nay), hoac None neu doan dang giu.
"""
import re
from typing import List, Optional

from .textbook_chunker import MIN_WORDS, split_fenced_blocks

# Tieu de cuoi (khong phan biet hoa thuong) thuoc danh sach nay -> bo ca doan (R7).
BLOCKED_HEADINGS = frozenset({
    "see also", "table of contents", "release notes", "changelog",
    "next steps", "further reading", "feedback", "what's next",
})
CODE_RATIO_LIMIT = 0.70   # ky tu trong khoi ``` / tong > 70% -> code_only
LIST_SHORT_WORDS = 4      # muc danh sach duoi 4 tu coi nhu muc muc-luc

_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_LINK_ONLY = re.compile(r"^(?:\[[^\]]*\]\([^)]*\)|<?https?://\S+>?)[\s.,;:]*$")


def _word_count(text: str) -> int:
    """So token co it nhat mot ky tu chu/so (bo dau gach dau dong, so URL la mot tu)."""
    return sum(1 for token in text.split() if re.search(r"\w", token))


def prose_word_count(body: str) -> int:
    """So tu cua phan van xuoi trong than doan, khong tinh khoi code."""
    return sum(_word_count(text) for text, is_code in split_fenced_blocks(body) if not is_code)


def _is_blocked_heading(heading_path: List[str]) -> bool:
    if not heading_path:
        return False
    last = heading_path[-1].replace("’", "'").strip().rstrip(":?").strip().lower()
    return last in BLOCKED_HEADINGS


def _code_ratio(body: str) -> float:
    total = len(body.strip())
    if not total:
        return 0.0
    return sum(len(text) for text, is_code in split_fenced_blocks(body) if is_code) / total


def _is_link_list(body: str) -> bool:
    """Hon mot nua so dong (ngoai khoi code) la muc danh sach chi co link hoac duoi 4 tu."""
    lines = [
        line.strip()
        for text, is_code in split_fenced_blocks(body) if not is_code
        for line in text.split("\n") if line.strip()
    ]
    if not lines:
        return False
    weak = 0
    for line in lines:
        match = _LIST_ITEM.match(line)
        if match:
            item = match.group(1).strip()
            if _LINK_ONLY.match(item) or _word_count(item) < LIST_SHORT_WORDS:
                weak += 1
    return weak * 2 > len(lines)


def noise_reason(heading_path: List[str], body: str) -> Optional[str]:
    """blocked_heading | code_only | link_list | too_short | None (giu)."""
    if _is_blocked_heading(heading_path):
        return "blocked_heading"
    if _code_ratio(body) > CODE_RATIO_LIMIT:
        return "code_only"
    if _is_link_list(body):
        return "link_list"
    if prose_word_count(body) < MIN_WORDS:
        return "too_short"
    return None
