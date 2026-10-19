"""Evaluator MOCK: cham bang heuristic tu khoa, khong LLM (thay bang Evaluator LLM o tuan 2).

Giu dung hinh dang Evaluation va cac luat hau kiem cua docs/ai-service/05 muc 6.2:
quote phai la doan nguyen van trong answer; dont_know/manipulation => moi band = 0;
completeness bi chan theo ti le key point co bang chung; luot sau hint => band <= 3.
"""
import math
import re
import unicodedata
from typing import List, Optional, Tuple

from . import cv_text
from .models_interview import Bands, Evaluation, Evidence, PlanTopic, Scores10

_STOP = {"duoc", "neu", "giai", "thich", "cach", "voi", "cho", "trong", "cua", "nhung", "mot", "cac", "khi", "theo"}
_DONT_KNOW = re.compile(r"(khong biet|chua biet|chua hoc|khong ro|khong nho|\bpass\b|bo qua|chua tung)")
_CLARIFY = re.compile(r"^(ban co the )?(nhac lai|hoi lai|y ban la|cau hoi la gi)")
_MANIP = re.compile(r"(cho (toi|em|minh|tui).{0,30}\d+\s*(/\s*10)?\s*diem|10\s*/\s*10|diem toi da|ignore (all|previous))")


def fold(text: str) -> str:
    """Bo dau tieng Viet + lower, de so khop khong phu thuoc dau."""
    t = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9#+.]+", fold(text)) if len(t) >= 4 and t not in _STOP}


def _sentences(answer: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?\n]+", answer) if s.strip()]


def _covered(point: str, answer_tokens: set) -> bool:
    pt = _tokens(point)
    return bool(pt) and len(pt & answer_tokens) / len(pt) >= 0.5


def _quote(point: str, answer: str) -> Optional[str]:
    pt = _tokens(point)
    best: Tuple[int, str] = (0, "")
    for s in _sentences(answer):
        n = len(pt & _tokens(s))
        if n > best[0]:
            best = (n, s)
    return best[1][:100] if best[0] else None


def _slug(point: str) -> str:
    return "-".join(sorted(_tokens(point))[:2]) or "general"


def classify_answer(answer: str, covered: int, question: str, topic: PlanTopic) -> str:
    f = fold(answer).strip()
    words = len(f.split())
    if _MANIP.search(f) or cv_text.has_injection(answer):
        return "manipulation"
    if words <= 6 and _DONT_KNOW.search(f):
        return "dont_know"
    if covered == 0 and words <= 15 and (f.endswith("?") or _CLARIFY.search(f)):
        return "asks_clarification"
    ctx = _tokens(question + " " + topic.title + " " + " ".join(topic.key_points))
    if covered == 0 and words >= 8 and not (ctx & _tokens(answer)):
        return "off_topic"
    return "partial" if 0 < covered and covered * 2 < len(topic.key_points) else "answered"


def evaluate(answer: str, question: str, topic: PlanTopic, turn_kind: str, turn_number: int) -> Evaluation:
    a_tokens = _tokens(answer)
    covered_pts = [p for p in topic.key_points if _covered(p, a_tokens)]
    missing = [p for p in topic.key_points if p not in covered_pts]
    atype = classify_answer(answer, len(covered_pts), question, topic)
    words = len(answer.split())
    ratio = len(covered_pts) / len(topic.key_points)

    bands = {
        "technical_accuracy": 0 if words < 3 else min(4, 1 + round(3 * ratio)),
        "completeness": min(4, math.ceil(4 * ratio)),
        "extensibility": 0 if words < 20 else 1 + (ratio >= 0.5) + (words >= 50 and ratio >= 0.67),
        "relevance": 4 if ratio > 0 else (2 if words >= 8 else 1),
    }
    if atype in ("dont_know", "manipulation"):
        bands = {k: 0 for k in bands}
    elif atype == "off_topic":
        bands["relevance"] = 0
    if turn_kind == "hint":
        bands = {k: min(v, 3) for k, v in bands.items()}
    evidence = []
    for p in covered_pts[:3]:
        q = _quote(p, answer)
        if q:  # luat hau kiem: quote phai nam nguyen van trong answer
            evidence.append(Evidence(claim=p, quote=q))
    score = sum(bands.values()) / 4
    return Evaluation(
        turn_number=turn_number, answer_type=atype,
        covered_points=covered_pts[:3], missing_points=missing[:3], misconceptions=[], evidence=evidence,
        scores=Bands(**bands), scores_10=Scores10(**{k: v * 2.5 for k, v in bands.items()}),
        turn_score_10=round(score * 2.5, 1),
        strength_tags=[_slug(p) for p in covered_pts[:3]], gap_tags=[_slug(p) for p in missing[:3]],
        follow_up_focus=(missing[0].replace("Nêu được ", "")[:150] if missing else None))


def turn_score(ev: Evaluation) -> float:
    """Diem luot theo thang band 0-4."""
    return ev.turn_score_10 / 2.5


def is_scored(ev: Evaluation) -> bool:
    """Luot clarify va degraded khong tinh diem (docs 05 muc 6.3)."""
    return ev.answer_type != "asks_clarification" and not ev.degraded
