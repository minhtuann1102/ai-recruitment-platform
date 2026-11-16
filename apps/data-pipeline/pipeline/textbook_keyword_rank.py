"""BM25 nho cho lenh coverage-textbook (spec 012, research R10): xep hang tu khoa tren cac doan da xu ly, offline.

Pipeline khong import code ai-service (005 R1), nen tokenize chep NGUYEN quy tac cua
apps/ai-service/app/rag/bm25_index.py::tokens (am tiet, bo tu chuc nang khoi token don, them cap am tiet lien nhau).
Cong thuc BM25 chuan voi k1 = 1.5 (ai-service dung 1.2) va b = 0.75; IDF khong am nhu ai-service. Day chi la ban xap
xi de do do phu truoc khi ton embedding; so do chinh thuc la cua AIE (SC-007).
"""
import math
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Sequence

K1, B = 1.5, 0.75

# Chep tu bm25_index.STOPWORDS (Viet co dau va khong dau + Anh)
STOPWORDS = frozenset("""
va la cua co khong cho nhu nao gi khi thi duoc trong voi mot cac nhung de bi tai sao vi neu ma hay hoac
và là của có không cho như nào gì khi thì được trong với một các những để bị tại sao vì nếu mà hãy hoặc
này đó thế làm ra vào lại đã đang sẽ rất cũng nhiều ít hơn bạn mình em anh chị ta họ giữa trên dưới sau trước
the a an of to in on for and or is are be was were it this that with as by at from how what why when which
do does can you your use using vs
""".split())


def tokenize(text: str) -> List[str]:
    """Token don (>= 2 ky tu, khong phai tu chuc nang) + cap tu lien nhau "a_b" dung tren MOI tu (ke ca tu chuc nang)."""
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text.lower()))
    single = [w for w in words if len(w) >= 2 and w not in STOPWORDS]
    return single + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def _default_text(doc: Any) -> str:
    """Doan = chuoi hoac dict ban ghi xu ly (data-model §3) co khoa "content"."""
    return doc if isinstance(doc, str) else doc["content"]


class Bm25:
    def __init__(self, docs: Sequence[Any], text_of: Callable[[Any], str] = _default_text):
        self.docs = list(docs)
        self._tf = [Counter(tokenize(text_of(d))) for d in self.docs]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = (sum(self._len) / len(self._len)) if self._len else 1.0
        df = Counter(w for tf in self._tf for w in tf)
        n = len(self.docs)
        self._idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self._postings: Dict[str, List[int]] = defaultdict(list)
        for i, tf in enumerate(self._tf):
            for w in tf:
                self._postings[w].append(i)

    def top(self, query: str, k: int, allow: Optional[Callable[[Any], bool]] = None) -> List[Any]:
        """k doc diem cao nhat (chi doc co it nhat mot tu cua truy van); `allow` loc TRUOC khi cat k."""
        scores: Dict[int, float] = defaultdict(float)
        for w in set(tokenize(query)):
            idf = self._idf.get(w)
            if not idf:
                continue
            for i in self._postings[w]:
                f = self._tf[i][w]
                scores[i] += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * self._len[i] / self._avg))
        ranked = sorted((i for i in scores if allow is None or allow(self.docs[i])), key=lambda i: (-scores[i], i))
        return [self.docs[i] for i in ranked[:k]]
