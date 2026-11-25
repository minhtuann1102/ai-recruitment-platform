"""Chuan hoa ban ghi, tach token va dem tu dem (research R5).

Mot quy tac duy nhat cho ca chi so trinh bay (delivery_metrics) va bo do (evals/wer.py):
- Unicode NFC truoc (STT co the tra dang to hop roi, NFC giu dau tieng Viet nguyen ven), roi chu thuong.
- Dau noi (-, –, —), "/" va "_" thanh khoang trang (noi thanh hai tu: "thread-safe", "CI/CD"); dau cau khac bo han
  ("don't" -> "dont", "3.5" -> "35"). Giu nguyen dau thanh / dau mu cua tieng Viet.
- Token = chuoi cach nhau boi khoang trang. Tieng Viet moi token la mot am tiet, thuat ngu tieng Anh moi token la mot tu;
  goi chung "am tiet" trong bao cao.
"""
import unicodedata
from typing import Iterable, List, Sequence, Tuple

_CONNECTORS = "/_"


def normalize(text: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFC", text).lower():
        category = unicodedata.category(ch)
        if category == "Pd" or ch in _CONNECTORS:
            out.append(" ")
        elif not category.startswith("P"):
            out.append(ch)
    return "".join(out)


def tokens(text: str) -> List[str]:
    return normalize(text).split()


def count_fillers(token_list: Sequence[str], fillers: Iterable[str]) -> int:
    """So token thuoc tu dem. Khop cum dai truoc ("kieu nhu" truoc "nhu"); cum khop xong khong khop lai.
    Tu dem la danh sach cau hinh (Settings.fillers); "a" dung mot minh khong nam trong danh sach mac dinh."""
    phrases: List[Tuple[str, ...]] = sorted({tuple(tokens(f)) for f in fillers if tokens(f)}, key=len, reverse=True)
    count = i = 0
    while i < len(token_list):
        for phrase in phrases:
            size = len(phrase)
            if tuple(token_list[i:i + size]) == phrase:
                count += size
                i += size
                break
        else:
            i += 1
    return count
