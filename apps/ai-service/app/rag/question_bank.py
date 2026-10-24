"""Ngan hang cau hoi tu kho interview_qa cua DE (da thu thap va kiem chung, tieng Viet giu thuat ngu Anh).

Luc start: moi topic ky thuat lay cac cap Q&A theo topic_id, bo cau khong doc thanh tieng duoc (co code, nhieu dong,
qua dai), xep theo do sat voi topic (title + key_points) roi do kho -> PlanTopic.bank_questions (chi cau hoi + qa_id).
Moi luot ask_main chon mot cau chua dung; Interviewer dien dat lai. Dap an chuan (ca cap Q&A) giu trong cache cua
process, Evaluator lay theo qa_id; cache truot (replica khac, restart) thi doc lai tu ai_db.
"""
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from ..text_similarity import words

MAX_QUESTION_CHARS = 200
ANSWER_KEY_CHARS = 1800  # ~600 token (uoc 3 ky tu/token), du cho mot dap an chuan
_MARKDOWN = re.compile(r"[*_#`>]+")


@dataclass(frozen=True)
class BankEntry:
    qa_id: str
    question: str
    difficulty: Optional[str]
    pair: str  # cau hoi + dap an (noi dung chunk qa_pair)


def spoken_ok(question: str) -> bool:
    """Cau hoi dung duoc trong phong van noi: mot dong, khong khoi code, khong qua dai."""
    q = question.strip()
    return bool(q) and "\n" not in q and "```" not in q and len(q) <= MAX_QUESTION_CHARS


def plain(question: str) -> str:
    """Bo ky hieu markdown (vd `HashMap`) de dung nguyen van lam cau du phong / dua cho Interviewer."""
    return " ".join(_MARKDOWN.sub("", question).split())


def rank(entries: Sequence[BankEntry], topic_terms: Iterable[str], bucket: Optional[str], n: int,
         generic: Iterable[str] = ()) -> List[BankEntry]:
    """Chi giu cau co it nhat mot tu chung voi topic (title, key_points, key_concepts), khong tinh tu chung cua ca
    track ("java", "backend") vi topic_id trong kho gan rong (vd cau doc input console nam o topic HashMap).
    Cau sat hon truoc, cung muc thi uu tien dung do kho. Khong cau nao dat: tra rong, Interviewer tu dat cau."""
    stop = {w for t in generic for w in words(t)}
    terms = {w for t in topic_terms for w in words(t) if len(w) > 2} - stop  # bo hu tu ngan ("va", "la", "gi")
    scored = [(len(words(e.question) & terms), e) for e in entries if spoken_ok(e.question)]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: (-x[0], x[1].difficulty != bucket, x[1].qa_id))
    return [e for _, e in scored[:n]]


def pick(bank: Sequence, used: Sequence[str], bucket: Optional[str]):
    """Chon cau chua dung trong phien; uu tien dung do kho hien tai. bank: list BankQuestion cua PlanTopic."""
    fresh = [b for b in bank if b.qa_id not in used]
    return next((b for b in fresh if b.difficulty == bucket), fresh[0] if fresh else None)


class AnswerCache:
    """LRU qa_id -> cap Q&A. Chi la toi uu do tre: service van stateless, cache truot thi doc lai ai_db."""

    def __init__(self, size: int = 2000):
        self.size, self._data = size, OrderedDict()

    def put(self, qa_id: str, pair: str) -> None:
        self._data[qa_id] = pair[:ANSWER_KEY_CHARS]
        self._data.move_to_end(qa_id)
        while len(self._data) > self.size:
            self._data.popitem(last=False)

    def get(self, qa_id: str) -> Optional[str]:
        if qa_id in self._data:
            self._data.move_to_end(qa_id)
            return self._data[qa_id]
        return None
