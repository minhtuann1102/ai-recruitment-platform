"""Do loi nhan dang cho bo do (spec 015 FR-021, T025): ty le loi am tiet va ty le nhan dung thuat ngu.

Tu viet, khong them thu vien. Dung chung `app.transcript_tokens.tokens` voi chi so trinh bay: cung quy tac chuan hoa
(NFC, chu thuong, bo dau cau, giu dau tieng Viet), nen "Ừm," va "ừm" la mot token. Chay tu thu muc apps/voice-service
(python -m evals.xxx) de import duoc `app`.
"""
from collections import Counter
from typing import Iterable, Optional, Sequence, Set, Tuple

from app.transcript_tokens import tokens


def edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    """Levenshtein theo token (thay, xoa, chen deu tinh 1)."""
    previous = list(range(len(hypothesis) + 1))
    for i, ref_token in enumerate(reference, start=1):
        current = [i]
        for j, hyp_token in enumerate(hypothesis, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ref_token != hyp_token)))
        previous = current
    return previous[-1]


def syllable_error_rate(reference: str, hypothesis: str) -> float:
    """(thay + xoa + chen) / so token ban chuan. Co the > 1.0 khi chen nhieu. Ban chuan rong thi khong co nghia."""
    ref = tokens(reference)
    if not ref:
        raise ValueError("ban chuan rong: khong tinh duoc ty le loi am tiet")
    return edit_distance(ref, tokens(hypothesis)) / len(ref)


def term_vocabulary(terms: Iterable[str]) -> Set[str]:
    """Token cua danh sach thuat ngu cua track (vd /api/stt/phrases): "Spring Boot" cho "spring" va "boot"."""
    return {token for term in terms for token in tokens(term)}


def term_recognition(reference: str, hypothesis: str, terms: Iterable[str]) -> Tuple[int, int]:
    """(so thuat ngu nhan dung, tong so thuat ngu trong ban chuan). Thuat ngu = token cua ban chuan co trong danh sach
    thuat ngu; nhan dung = token do con trong ban STT (khong phu thuoc vi tri, moi lan xuat hien dem mot lan)."""
    vocabulary = term_vocabulary(terms)
    wanted = Counter(token for token in tokens(reference) if token in vocabulary)
    got = Counter(tokens(hypothesis))
    return sum(min(count, got[token]) for token, count in wanted.items()), sum(wanted.values())


def term_recognition_rate(reference: str, hypothesis: str, terms: Iterable[str]) -> Optional[float]:
    """Ty le nhan dung thuat ngu (0..1); None khi ban chuan khong co thuat ngu nao (khong tinh vao SC-002)."""
    found, total = term_recognition(reference, hypothesis, terms)
    return found / total if total else None
