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
_LEVEL = {"easy": 0, "medium": 1, "hard": 2}


def gap(difficulty: Optional[str], bucket: Optional[str]) -> int:
    """So bac do kho lech nhau (easy/medium/hard); khong ro thi coi la lech 1."""
    if difficulty not in _LEVEL or bucket not in _LEVEL:
        return 1
    return abs(_LEVEL[difficulty] - _LEVEL[bucket])


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
    Dung do kho truoc (kho chi ~4% cau hard), roi cau sat topic hon. Khong cau nao dat: tra rong, Interviewer tu
    dat cau."""
    stop = {w for t in generic for w in words(t)}
    terms = {w for t in topic_terms for w in words(t) if len(w) > 2} - stop  # bo hu tu ngan ("va", "la", "gi")
    scored = [(len(words(e.question) & terms), e) for e in entries if spoken_ok(e.question)]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: (gap(x[1].difficulty, bucket), -x[0], x[1].qa_id))
    return [e for _, e in scored[:n]]


KEEP_MEANING_MIN = 0.5


def kept_meaning(bank_question: str, asked: str) -> bool:
    """Interviewer co giu y cau trong kho khong: >= 50% tu (> 2 ky tu) cua cau goc co trong cau da hoi. Cau dan them
    phia truoc khong lam giam; doi sang y khac (vd danh sach package -> middleware noi chung) thi rot -> khong dung
    dap an chuan cho luot do."""
    original = {w for w in words(bank_question) if len(w) > 2}
    return not original or len(original & words(asked)) / len(original) >= KEEP_MEANING_MIN


def pick(bank: Sequence, used: Sequence[str], bucket: Optional[str]):
    """Chon cau chua dung trong phien, gan do kho hien tai nhat; lech 2 bac (cau easy khi dang o muc hard) thi khong
    dung, Interviewer tu dat cau dung do kho. bank: list BankQuestion cua PlanTopic."""
    fresh = sorted((b for b in bank if b.qa_id not in used and gap(b.difficulty, bucket) < 2),
                   key=lambda b: gap(b.difficulty, bucket))
    return fresh[0] if fresh else None


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
