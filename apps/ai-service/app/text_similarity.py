"""Do giong nhau giua hai cau (Jaccard tren tap tu da bo dau), dung chung cho chong lap cau hoi (FR-AI-038)
va chon focus khong trung (app/focus.py)."""
import re
from typing import Iterable

from .mock_evaluator import fold

REPEAT_JACCARD = 0.8


def words(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", fold(text)))


def jaccard(a: str, b: str) -> float:
    x, y = words(a), words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def is_repeat(question: str, asked: Iterable[str], threshold: float = REPEAT_JACCARD) -> bool:
    return any(jaccard(question, q) >= threshold for q in asked)
