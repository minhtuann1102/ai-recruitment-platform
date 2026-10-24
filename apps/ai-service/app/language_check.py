"""Kiem ngon ngu van ban AI gui cho ung vien: cau tieng Viet, giu thuat ngu tieng Anh (prompt Interviewer, Reporter).

Vi pham = mot cau co >= MIN_WORDS tu Latin, khong co ky tu tieng Viet co dau va co >= 2 hu tu tieng Anh (cau tieng
Anh tron cau, vd LLM chay theo ngon ngu cua ung vien) hoac >= 2 hu tu tieng Viet khong dau. Chuoi thuat ngu
("CSR vs SSR vs SSG vs ISR", "ConcurrentHashMap vs Hashtable?") khong co hu tu nen khong tinh. Ham thuan, dung chung cho harness (evals) va guard dau ra.
"""
import re
from typing import List

MIN_WORDS = 6
_VI = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE)
_SENTENCE = re.compile(r"[^.?!;:\n]+")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'+#-]*")
_EN = {"the", "a", "an", "is", "are", "was", "be", "you", "your", "i", "we", "it", "this", "that", "of", "to", "in",
       "for", "with", "how", "what", "why", "when", "can", "could", "would", "do", "does", "and", "or", "about"}
_VI_PLAIN = {"ban", "la", "cua", "khong", "va", "duoc", "nhu", "mot", "cho", "voi", "nhung", "trong", "minh", "em"}


def english_sentences(text: str, min_words: int = MIN_WORDS) -> List[str]:
    """Cac cau khong co dau tieng Viet va co it nhat min_words tu Latin."""
    out = []
    for raw in _SENTENCE.findall(text or ""):
        sentence = raw.strip()
        words = [w.lower() for w in _WORD.findall(sentence)]
        if len(words) < min_words or _VI.search(sentence):
            continue
        if sum(w in _EN for w in words) >= 2 or sum(w in _VI_PLAIN for w in words) >= 2:
            out.append(sentence)
    return out


def wrong_language(text: str) -> bool:
    return bool(english_sentences(text))
