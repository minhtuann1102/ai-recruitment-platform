"""Danh sach thuat ngu goi y cho dich vu STT (NFR-AI-QUAL16/17): sua tu nguon thay vi doi sau bang stt_terms.

Google / Azure nhan phrase list, Whisper nhan prompt: backend (noi goi STT) lay danh sach theo track qua
GET /api/stt/phrases. Nguon: cum chu Latin trong title + key_concepts cua catalog track (thu tu catalog), roi thuat
ngu chung trong STT_TERMS. Catalog viet tieng Viet co dau nen chu Latin gan nhu chac la thuat ngu; tu tieng Viet viet
khong dau ("chung", "tra") la ngoai le: chan bang _VI_WORDS va bo tu don ngan viet thuong. Heuristic: danh sach
cach nhau bang dau cach trong catalog ("LCP INP CLS") thanh mot cum, tu chung ("model", "output") van lot qua.
"""
import re
from functools import lru_cache
from typing import List, Tuple

from .mock_planner import load_track
from .stt_terms import STT_TERMS

_LATIN = re.compile(r"^[A-Za-z0-9@][A-Za-z0-9+#./@_-]*$")
_VI_WORDS = {"an", "ban", "cao", "chi", "chia", "cho", "chung", "con", "giao", "hay", "hoac", "khai", "khi", "ma",
             "mo", "ngang", "pha", "qua", "quan", "quy", "ra", "ro", "sau", "tay", "tham", "theo", "thi", "thu", "tim",
             "tin", "toan", "tra", "trong", "truy", "va", "vai", "vs"}
SHORT_WORD = 4  # tu don viet thuong <= 4 chu ("ra", "khai", nhung ca "list", "heap") de STT tu nhan


def _is_term_word(word: str) -> bool:
    return bool(_LATIN.match(word)) and bool(re.search("[A-Za-z]", word)) and word.lower() not in _VI_WORDS


def _keep(phrase: str) -> bool:
    return " " in phrase or len(phrase) > SHORT_WORD or not phrase.islower()


def latin_phrases(text: str) -> List[str]:
    """Cum tu Latin lien tiep trong mot dong catalog ("thread pool và ExecutorService" -> 2 cum)."""
    out = []
    for segment in re.split(r"[,;()]", text):  # dau cau ngat cum: "Next.js, SSR" la 2 cum
        cur: List[str] = []
        for raw in segment.split() + [""]:
            word = raw.strip(".:")
            if word and (_is_term_word(word) or (cur and word.isdigit())):  # "OWASP Top 10": so di theo cum
                cur.append(word)
            elif cur:
                out.append(" ".join(cur))
                cur = []
    return [p for p in out if _keep(p)]


@lru_cache(maxsize=None)
def track_phrases(track: str) -> Tuple[str, ...]:
    """Thuat ngu cua track truoc (dich vu gioi han so cum thi cat duoi), sau do thuat ngu chung; khong trung."""
    catalog = load_track(track)  # track la -> ApiError 422
    found = [p for t in catalog.topics for line in (t.title, *t.key_concepts) for p in latin_phrases(line)]
    return tuple(dict.fromkeys([*found, *STT_TERMS]))
