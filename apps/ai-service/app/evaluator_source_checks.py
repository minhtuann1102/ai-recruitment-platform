"""Hau kiem trich nguon cua Evaluator v4 (plans/261029-1415-hybrid-grounded-rag, Phase 03a).

Moi tai lieu doi chieu trong luot co id do code gan theo thu tu gui: S1..Sn (snippet cua topic truoc, chunk theo
luot sau), R (dap an chuan cua cau tu kho). LLM ghi `source_ids` + `support` cho tung y covered; code quyet dinh:
id khong co trong luot bi bo, het id thi `no_source`; `contradicted` co id hop le thi y do khong duoc tinh covered,
va chi khi dap an chuan (R) bac bo thi moi thanh hieu sai (luat 4, chan technical_accuracy): snippet / chunk theo
luot chi gan dung chu de (BM25), mot chunk lech khong du de chan diem.
"""
import unicodedata
from difflib import SequenceMatcher
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .mock_evaluator import fold

REFERENCE_ID = "R"
MAX_SOURCE_IDS = 3
MIN_RESTATED_WORDS = 6  # cum ngan de trung tinh co; model chep nguyen cau dap an nen khong can khop mo
NEGATOR_WINDOW = 3
_NEGATORS = frozenset({"không", "chưa", "chẳng", "đừng", "tránh", "thay", "sai", "lầm", "nhầm", "trước", "not",
                       "never", "cannot", "no", "t", "without", "avoid", "wrong"})


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


def refuted_by_reference(contradicted: Sequence[SourcedPoint], reference_answer: str) -> List[str]:
    """Dieu ung vien noi sai: `quote` da kiem trong cau tra loi, vi `point` thuong chep y dung cua R du prompt dan khac.
    `point` chep nguyen cau cua R la y ung vien chua neu, khong phai bac bo."""
    return [p.quote for p in contradicted
            if REFERENCE_ID in p.source_ids and not restates_reference(p.point, reference_answer)]


def _similar(m: str, r: str, min_ratio: float = 0.8) -> bool:
    return SequenceMatcher(None, m.lower(), r.lower()).ratio() >= min_ratio or r.lower() in m.lower()


def merge_misconceptions(refuted: Sequence[str], llm: Sequence[str], min_ratio: float = 0.8) -> List[str]:
    """Y code da kiem (R bac bo) dung truoc de khong bi cat khi chi giu 2; bo y LLM gan trung."""
    out = list(dict.fromkeys(refuted))
    for m in llm:
        if not any(_similar(m, r, min_ratio) for r in out):
            out.append(m)
    return out


def is_tool_id(source_id: str, base_ids: int) -> bool:
    """S{n} voi n > base_ids: chunk Evaluator tra cuu duoc (noi cuoi turn_snippets), khong phai tai lieu co san."""
    return source_id.startswith("S") and source_id[1:].isdigit() and int(source_id[1:]) > base_ids


def split_tool_misconceptions(misconceptions: Sequence[str], contradicted: Sequence[SourcedPoint], base_ids: int
                              ) -> Tuple[List[str], List[str]]:
    """Luat "chi R bac" o luot co chunk cong cu (phase 03): chunk do duoc tim theo truy van bi cau tra loi lai nen khong
    du de chan technical_accuracy. Tra (chan, khong chan): khong chan = hieu sai LLM ghi khop `point` / `quote` cua y
    contradicted ma MOI id hop le deu la id cong cu. Hieu sai khac (khong gan nguon, hay dua tren snippet co san, hay
    id lan) chan nhu khi tat co. Hai danh sach van deu vao bao cao."""
    tool_only = [t for p in contradicted if p.source_ids and all(is_tool_id(i, base_ids) for i in p.source_ids)
                 for t in (p.point, p.quote) if t.strip()]
    free = [m for m in misconceptions if any(_similar(m, t) for t in tool_only)]
    return [m for m in misconceptions if m not in free], free


def _tokens(text: str) -> List[str]:
    return "".join(c if c.isalnum() else " " for c in unicodedata.normalize("NFC", text.lower())).split()


def restates_reference(text: str, reference_answer: str) -> bool:
    """Cau gan nhu nguyen van trong dap an chuan la y dung cua dap an, khong phai dieu ung vien hieu sai: model hay chep
    y ung vien chua neu cua R vao misconceptions (mo phong 02/11). Co tu phu dinh quanh bat ky lan xuat hien nao (R co
    the dang bac bo chinh cau do, vd "khong khoa toan bo map") thi coi la chua chac, giu lai de khong bo sot hieu sai."""
    phrase, words = [fold(w) for w in _tokens(text)], _tokens(reference_answer)
    folded, size = [fold(w) for w in words], len(phrase)
    hits = [i for i in range(len(words) - size + 1) if folded[i:i + size] == phrase]
    if size < MIN_RESTATED_WORDS or not hits:
        return False
    # so tren tu con dau: neu bo dau, dai tu "no" va dong tu "chua" (chứa) se trung tu phu dinh
    around = (words[max(0, i - NEGATOR_WINDOW):i] + words[i + size:i + size + NEGATOR_WINDOW] for i in hits)
    return not any(_NEGATORS.intersection(window) for window in around)


def confidence(kept: Sequence[SourcedPoint], has_sources: bool) -> Optional[str]:
    """low: co tai lieu, co y covered nhung khong y nao duoc tai lieu ung ho. Khong tai lieu / khong y nao: None."""
    if not kept or not has_sources:
        return None
    return "high" if any(p.support == "supported" for p in kept) else "low"
