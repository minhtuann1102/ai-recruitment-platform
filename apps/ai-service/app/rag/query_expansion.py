"""Mo rong truy van tieng Viet bang thuat ngu tieng Anh truoc khi embed (rag-design muc 7.4).

Do 24/10: recall@5 nhom tieng Viet thuan 0.667, thap nhat; kho Q&A giu thuat ngu Anh (index, cache, transaction...)
nen truy van chi co tu Viet ("phan trang", "bang bam") khop kem. Ham nay noi them thuat ngu Anh tuong ung, so
khop tren chuoi da bo dau nen ap dung ca cho truy van khong dau. Tu dien la thuat ngu IT pho bien, khong viet
rieng cho golden set: cac cum chep tu cau trong golden set ("bo qua so dong", "tru ton kho"...) da bi bo de
khong thoi phong recall (so do 24/10 ghi ca hai ban).
"""
import re
from typing import List

from ..mock_evaluator import fold

# cum tu Viet (da bo dau) -> thuat ngu Anh. Cum dai dat truoc de khop truoc. Khong dung khoa mot tu de nham
# sau khi bo dau ("luong" = luong/luong/luong: chat luong, so luong, luong) hay tu thong dung ("danh gia",
# "mo rong", "dong thoi", "trien khai", "giao dien") vi them nhieu vao hau het truy van.
GLOSSARY = {
    "bang bam": "hash table HashMap", "ham bam": "hash function hashCode", "phan trang": "pagination offset limit",
    "chi muc": "index", "danh chi muc": "index", "truy van": "query SQL",
    "khoa chinh": "primary key", "khoa ngoai": "foreign key", "giao dich": "transaction",
    "muc co lap": "isolation level", "khoa lac quan": "optimistic locking", "khoa bi quan": "pessimistic locking",
    "cap nhat dong thoi": "concurrent update race condition lost update",
    "truy cap dong thoi": "concurrent access concurrency", "da luong": "multithreading thread",
    "luong xu ly": "thread", "tien trinh": "process",
    "bat dong bo": "asynchronous async await", "vong lap su kien": "event loop", "hang doi": "queue message queue",
    "bo nho dem": "cache", "bo nho dem phan tan": "distributed cache Redis", "ro ri bo nho": "memory leak",
    "thu gom rac": "garbage collection GC", "tran bo nho": "out of memory OOM", "bo nho heap": "heap memory",
    "do tre": "latency", "thong luong": "throughput", "tai cao": "high load scaling",
    "kha nang mo rong": "scalability",
    "can bang tai": "load balancer", "chiu loi": "fault tolerance", "thu lai": "retry", "luy dang": "idempotent",
    "ton kho": "inventory stock", "xac thuc": "authentication", "phan quyen": "authorization",
    "ma thong bao": "token JWT", "lam moi phien": "refresh token session", "kiem thu": "testing test",
    "kiem thu don vi": "unit test", "gia lap": "mock", "trien khai len": "deployment deploy",
    "vung chua": "container", "dieu phoi container": "Kubernetes orchestration", "giam sat": "monitoring",
    "nhat ky": "logging log", "canh bao": "alert alerting", "kien truc": "architecture",
    "vi dich vu": "microservices", "mo hinh ngon ngu": "language model LLM", "tinh chinh": "fine-tuning",
    "truy hoi": "retrieval RAG", "nhung vector": "embedding vector", "do tuong dong": "similarity",
    "danh gia mo hinh": "model evaluation", "ao giac": "hallucination", "tiem lenh": "prompt injection",
    "ke thua": "inheritance", "da hinh": "polymorphism", "dong goi": "encapsulation",
    "kiem dinh cheo": "cross-validation", "ro ri du lieu": "data leakage", "qua khop": "overfitting",
}
_KEYS = sorted(GLOSSARY, key=len, reverse=True)


def english_terms(query: str) -> List[str]:
    """Thuat ngu Anh cho cac cum Viet xuat hien trong truy van (khop tron tu tren chuoi da bo dau)."""
    text = " " + " ".join(re.findall(r"[a-z0-9]+", fold(query))) + " "
    found: List[str] = []
    for key in _KEYS:
        if f" {key} " in text:
            text = text.replace(f" {key} ", " ")  # cum dai da khop thi khong khop lai cum con
            if GLOSSARY[key] not in found:
                found.append(GLOSSARY[key])
    return found


def expand_query(query: str) -> str:
    """Giu nguyen truy van, noi them thuat ngu Anh neu co. Truy van da co thuat ngu Anh van duoc giu nguyen."""
    terms = english_terms(query)
    return f"{query} ({'; '.join(terms)})" if terms else query
