"""Hau kiem Evaluation bang code (FR-AI-031, 032; docs/ai-service/05 muc 6.2 "luat khat khe").

LLM chi de xuat; code quyet dinh: quote khong co trong cau tra loi thi y do bi xoa, completeness bi chan
theo ti le key point co bang chung, misconception -> technical_accuracy <= 1, sau hint -> moi band <= 3,
dont_know / manipulation -> moi band = 0, off_topic -> relevance = 0, chi liet ke thuat ngu -> completeness va
extensibility <= 1, relevance <= 2.
"""
import math
import re
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Sequence

from .mock_evaluator import fold, is_manipulation
from .models_interview import Bands, CitedSource, Evaluation, Evidence, Scores10

QUOTE_MIN_RATIO = 0.9  # FR-AI-031: quote khop fuzzy >= 0.9 sau chuan hoa
QUOTE_MIN_WORDS = 3  # quote 1-2 tu ("Index", "khong") khong du lam bang chung cho mot y
POINT_MIN_RATIO = 0.8  # y LLM ghi la covered phai gan trung mot key point moi tinh vao completeness
MAX_COVERED = 4  # chan so y can kiem (moi y mot lan quet fuzzy) de khong chan event loop
ZERO_TYPES = ("dont_know", "manipulation")
TERM_LIST_MIN_ITEMS, TERM_MAX_WORDS, TERM_LIST_RATIO = 6, 3, 0.8  # luat 5: nhoi thuat ngu, khong co cau giai thich

# Cum "khong biet" va tu dem; dont_know chi khi bo het nhung tu nay thi khong con gi (FR-AI-032)
_DONT_KNOW_PHRASES = ("khong biet", "chua biet", "chua hoc", "khong ro", "khong nho", "chua tung hoc",
                      "chua tung lam", "chua tung dung", "chiu", "bo qua", "pass", "xin phep bo qua")
_FILLER = {"da", "a", "em", "anh", "chi", "minh", "toi", "tui", "that", "su", "thuc", "cau", "nay", "phan",
           "cai", "xin", "loi", "lam", "qua", "nhe", "oi", "vay", "roi", "thi", "ve", "van", "de", "cho", "y"}


def _norm(text: str) -> str:
    return " ".join(fold(text).split())


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9#+]+(?:[-.][a-z0-9]+)*", fold(text))


def precheck_answer(answer: str) -> Optional[str]:
    """Nhan dien bang code, khong goi Evaluator: 'manipulation', 'dont_know' hoac None.

    dont_know chi khi cau tra loi CHI gom cum "khong biet" va tu dem (<= 6 tu); "Java luon pass by value"
    hay "Bo qua cache, doc DB" van duoc cham.
    """
    if is_manipulation(answer):
        return "manipulation"
    words = _words(answer)
    if not words or len(words) > 6:
        return None
    rest = " " + " ".join(words) + " "
    found = False
    for phrase in _DONT_KNOW_PHRASES:
        if f" {phrase} " in rest:
            found, rest = True, rest.replace(f" {phrase} ", " ")
    return "dont_know" if found and all(w in _FILLER for w in rest.split()) else None


def quote_in_answer(quote: str, answer: str, min_ratio: float = QUOTE_MIN_RATIO) -> bool:
    """Quote phai nam trong answer: khop nguyen van sau chuan hoa, hoac khop fuzzy cua so cung so tu.

    Fuzzy chi tha cho sai khac nho khi LLM chep lai (dau, gach noi): quote < 5 tu phai co du moi tu trong
    answer, quote dai hon duoc thieu toi da 1 tu ("read committed" khong khop "read uncommitted").
    """
    q, a = _norm(quote), _norm(answer)
    q_words = _words(quote)
    if len(q_words) < QUOTE_MIN_WORDS:
        return False
    if q in a:
        return True
    answer_words = set(_words(answer))
    if sum(1 for w in q_words if w not in answer_words) > (1 if len(q_words) >= 5 else 0):
        return False
    words, n = a.split(), len(q.split())
    matcher = SequenceMatcher(None, autojunk=False)
    matcher.set_seq2(q)  # seq2 co dinh: SequenceMatcher cache thong tin seq2
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(0, max(1, len(words) - size + 1)):
            matcher.set_seq1(" ".join(words[i:i + size]))
            if matcher.real_quick_ratio() >= min_ratio and matcher.quick_ratio() >= min_ratio \
                    and matcher.ratio() >= min_ratio:
                return True
    return False


# Tu chuc nang pho bien (da bo dau) khong tinh la "tu chung" giua quote va point
_COMMON = {"dung", "duoc", "cho", "khi", "voi", "trong", "cua", "cac", "mot", "nhung", "neu", "thi", "va",
           "de", "khong", "nen", "theo", "the", "nao", "hay", "hoac", "lai", "vao", "len", "bang", "nhu", "phai",
           "can", "dang", "con", "nay", "do", "rat", "hon", "nhieu", "it", "cung", "tat", "ca", "moi",
           "and", "for", "with", "use"}


def _content_words(text: str) -> set:
    return {w for w in _words(text) if len(w) >= 3 and w not in _COMMON}


def supports_point(quote: str, point: str) -> bool:
    """Quote phai lien quan toi y no chung minh: co it nhat mot tu noi dung chung voi point."""
    return bool(_content_words(quote) & _content_words(point))


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def matched_key_points(points: Sequence[str], key_points: Sequence[str]) -> int:
    """So key point (khac nhau) duoc it nhat mot y covered da kiem chung khop."""
    return sum(1 for k in key_points if any(_similar(p, k) >= POINT_MIN_RATIO for p in points))


def is_term_list(answer: str) -> bool:
    """Cau tra loi chi liet ke ten: phan lon doan ngan cach boi dau phay chi 1-3 tu, khong co cau giai thich."""
    items = [i for i in re.split(r"[,;\n]+", answer) if i.strip()]
    short = sum(1 for i in items if len(i.split()) <= TERM_MAX_WORDS)
    return len(items) >= TERM_LIST_MIN_ITEMS and short >= TERM_LIST_RATIO * len(items)


def apply_caps(bands: Dict[str, int], *, answer_type: str, verified_key_points: int, total_key_points: int,
               has_misconception: bool, turn_kind: str, term_list: bool = False) -> Dict[str, int]:
    """Ap cac tran cua luat khat khe; tra ve dict band moi (khong sua dau vao)."""
    out = {k: max(0, min(4, int(v))) for k, v in bands.items()}
    if answer_type in ZERO_TYPES:
        return {k: 0 for k in out}
    if answer_type == "off_topic":
        out["relevance"] = 0
    if total_key_points:
        out["completeness"] = min(out["completeness"], math.ceil(4 * verified_key_points / total_key_points))
    if has_misconception:
        out["technical_accuracy"] = min(out["technical_accuracy"], 1)
    if term_list:
        out = {**out, "completeness": min(out["completeness"], 1), "extensibility": min(out["extensibility"], 1),
               "relevance": min(out["relevance"], 2)}
    if turn_kind == "hint":
        out = {k: min(v, 3) for k, v in out.items()}
    return out


def build_evaluation(*, turn_number: int, answer_type: str, bands: Dict[str, int],
                     covered_points: List[str] = (), missing_points: List[str] = (),
                     misconceptions: List[str] = (), evidence: List[Evidence] = (),
                     strength_tags: List[str] = (), gap_tags: List[str] = (),
                     follow_up_focus: Optional[str] = None, degraded: bool = False,
                     confidence: Optional[str] = None, sources: List[CitedSource] = ()) -> Evaluation:
    """Dung Evaluation tu band da hau kiem: band x 2.5 -> thang 0-10, diem luot = trung binh (docs 05 muc 6.1)."""
    return Evaluation(
        turn_number=turn_number, answer_type=answer_type, covered_points=list(covered_points)[:MAX_COVERED],
        missing_points=list(missing_points)[:3], misconceptions=list(misconceptions)[:2],
        evidence=list(evidence)[:MAX_COVERED], scores=Bands(**bands),
        scores_10=Scores10(**{k: v * 2.5 for k, v in bands.items()}),
        turn_score_10=round(sum(bands.values()) / 4 * 2.5, 1), degraded=degraded,
        strength_tags=list(strength_tags)[:3], gap_tags=list(gap_tags)[:3],
        follow_up_focus=(follow_up_focus or None) and follow_up_focus[:150], confidence=confidence,
        sources=list(sources))


def slug_tags(points: Iterable[str], limit: int = 3) -> List[str]:
    """Tag dang slug tu cau mo ta y ("Self-invocation khong qua proxy" -> "self-invocation-khong-qua"),
    dung cho strengths/gaps trong state; toi da 4 tu dau, bo trung."""
    tags: List[str] = []
    for p in points:
        slug = "-".join(_words(p)[:4])
        if slug and slug not in tags:
            tags.append(slug)
    return tags[:limit]


def zero_evaluation(turn_number: int, answer_type: str, gap_tags: List[str] = ()) -> Evaluation:
    """dont_know / manipulation do code nhan dien: moi band 0, khong goi LLM."""
    zero = {"technical_accuracy": 0, "completeness": 0, "extensibility": 0, "relevance": 0}
    return build_evaluation(turn_number=turn_number, answer_type=answer_type, bands=zero, gap_tags=list(gap_tags))
