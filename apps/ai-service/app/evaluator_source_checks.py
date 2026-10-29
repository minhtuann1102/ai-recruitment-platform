"""Hau kiem trich nguon cua Evaluator v4 (plans/261029-1415-hybrid-grounded-rag, Phase 03a).

Moi tai lieu doi chieu trong luot co id do code gan theo thu tu gui: S1..Sn (snippet cua topic truoc, chunk theo
luot sau), R (dap an chuan cua cau tu kho). LLM ghi `source_ids` + `support` cho tung y covered; code quyet dinh:
id khong co trong luot bi bo, het id thi `no_source`; `contradicted` co id hop le thi y do khong duoc tinh covered,
va chi khi dap an chuan (R) bac bo thi moi thanh hieu sai (luat 4, chan technical_accuracy): snippet / chunk theo
luot chi gan dung chu de (BM25), mot chunk lech khong du de chan diem.
"""
from difflib import SequenceMatcher
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

REFERENCE_ID = "R"
MAX_SOURCE_IDS = 3


def source_blocks(snippets: Sequence[str], reference_answer: str) -> List[Tuple[str, str]]:
    """(id, noi dung) cua moi tai lieu trong luot, dung thu tu dua vao prompt."""
    blocks = [(f"S{i}", s) for i, s in enumerate(snippets, 1)]
    return blocks + ([(REFERENCE_ID, reference_answer)] if reference_answer else [])


def label(block_id: str, text: str) -> str:
    return f"[{block_id}] {text}"


@dataclass
class SourcedPoint:
    point: str
    quote: str
    source_ids: List[str]
    support: str  # supported | contradicted | no_source


def check_sources(points: Sequence[SourcedPoint], valid_ids: Sequence[str]
                  ) -> Tuple[List[SourcedPoint], List[SourcedPoint], int]:
    """Tra (y giu lai, y tai lieu bac bo (bo khoi covered), so id khong hop le da bo)."""
    valid = set(valid_ids)
    kept, contradicted, invalid = [], [], 0
    for p in points:
        ids = list(dict.fromkeys(i.strip().upper() for i in p.source_ids))  # bo trung, giu thu tu
        good = [i for i in ids if i in valid][:MAX_SOURCE_IDS]
        invalid += len([i for i in ids if i not in valid])
        support = p.support if p.support in ("supported", "contradicted") and good else "no_source"
        checked = SourcedPoint(p.point, p.quote, good if support != "no_source" else [], support)
        (contradicted if support == "contradicted" else kept).append(checked)
    return kept, contradicted, invalid


def refuted_by_reference(contradicted: Sequence[SourcedPoint]) -> List[str]:
    return [p.point for p in contradicted if REFERENCE_ID in p.source_ids]


def merge_misconceptions(refuted: Sequence[str], llm: Sequence[str], min_ratio: float = 0.8) -> List[str]:
    """Y code da kiem (R bac bo) dung truoc de khong bi cat khi chi giu 2; bo y LLM gan trung."""
    out = list(dict.fromkeys(refuted))
    for m in llm:
        if not any(SequenceMatcher(None, m.lower(), r.lower()).ratio() >= min_ratio or r.lower() in m.lower()
                   for r in out):
            out.append(m)
    return out


def confidence(kept: Sequence[SourcedPoint], has_sources: bool) -> Optional[str]:
    """low: co tai lieu, co y covered nhung khong y nao duoc tai lieu ung ho. Khong tai lieu / khong y nao: None."""
    if not kept or not has_sources:
        return None
    return "high" if any(p.support == "supported" for p in kept) else "low"
