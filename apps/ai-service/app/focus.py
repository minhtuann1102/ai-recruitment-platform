"""Chon `focus` cho follow-up va hint (docs/ai-service/04 muc 5.4) sao cho khong hoi lai mot y trong cung topic.

Truoc day luat 10 luon tra "trade-off, internals hoac edge case" va luat 8 luon lay missing_points[0], nen cac
luot follow-up giong nhau (34% cau lap o lan chay harness mock 22/10). Nay uu tien y cu the chua dung, theo topic.
"""
import re
from typing import Iterable, List, Optional, Sequence

from .models_interview import Evaluation, PlanTopic
from .text_similarity import is_repeat, words

DEPTH = ("trade-off khi áp dụng {t}", "edge case hoặc lỗi hay gặp với {t}", "cơ chế bên trong của {t}",
         "ảnh hưởng khi hệ thống scale đối với {t}")


def same(a: str, b: str) -> bool:
    """Hai focus coi la cung mot y khi Jaccard >= 0.8 (cung nguong voi chong lap cau hoi)."""
    return is_repeat(a, [b])


def clean_point(point: str) -> str:
    """Bo tien to "Neu duoc" cua key point sinh boi plan du phong."""
    return re.sub(r"^nêu được\s+", "", point.strip(), flags=re.I)


def pick(candidates: Iterable[Optional[str]], used: Sequence[str]) -> Optional[str]:
    seen: List[str] = []
    for c in candidates:
        c = clean_point(c or "")
        if c and not any(same(c, u) for u in [*used, *seen]):
            return c
        seen.append(c)
    return None


def _content(text: str) -> set:
    return {w for w in words(clean_point(text)) if len(w) >= 3}


def covers(item: str, key_point: str) -> bool:
    """Y da neu `item` phu key point khi chua >= 50% tu noi dung cua key point (long hon Jaccard: "propagation
    REQUIRES_NEW" phu "Neu duoc propagation"), gan voi cach Evaluator gan y cho key point."""
    kp = _content(key_point)
    return bool(kp) and len(kp & _content(item)) / len(kp) >= 0.5


def _uncovered(topic: PlanTopic, covered: Sequence[str]) -> List[str]:
    return [k for k in topic.key_points if not any(covers(c, k) for c in covered)]


def gap_focus(ev: Evaluation, topic: PlanTopic, used: Sequence[str], covered: Sequence[str] = ()) -> Optional[str]:
    """Luat 8 va hint: y con thieu chua hoi, roi goi y cua Evaluator, roi key point chua duoc neu trong ca topic.
    covered: y da neu o cac luot truoc cua topic (cong them y cua luot nay)."""
    known = [*covered, *ev.covered_points]
    missing = [m for m in ev.missing_points if not any(covers(c, m) for c in known)]
    return pick([*missing, ev.follow_up_focus, *_uncovered(topic, known)], used)


def deepen_focus(ev: Evaluation, topic: PlanTopic, used: Sequence[str], covered: Sequence[str] = ()) -> Optional[str]:
    """Luat 10 (tra loi tot): key point chua neu trong ca topic, roi cac huong dao sau gan ten topic."""
    return pick([*_uncovered(topic, [*covered, *ev.covered_points]), *(d.format(t=topic.title) for d in DEPTH)],
                used)
