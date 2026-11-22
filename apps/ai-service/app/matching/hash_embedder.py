"""Embedding gia tat dinh cho che do mock va CI (spec 017 FR-015, research R8): bam token vao 1536 chieu roi chuan
hoa L2. Khong goi provider, khong can khoa; vector gia KHONG bao gio duoc ghi vao ai_db.

Dung hashlib chu khong dung hash() cua Python (hash() doi theo tien trinh nen khong tat dinh giua cac lan chay).
Cung token -> cung chieu, nen hai van ban chung nhieu tu co cosine cao: du de mock cho thu tu goi y co nghia.
"""
import hashlib
import re
import unicodedata
from typing import List

import numpy as np

from .scorer import l2_normalize

EMBEDDING_DIMS = 1536  # constitution IV: text-embedding-3-small
_TOKEN = re.compile(r"\w+")


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall(unicodedata.normalize("NFC", text or "").lower())


def hash_embed(text: str, dims: int = EMBEDDING_DIMS) -> np.ndarray:
    """Van ban -> vector float64 do dai dims, chuan hoa L2. Van ban khong co token -> vector 0 (khong NaN)."""
    vector = np.zeros(dims, dtype=np.float64)
    for token in tokenize(text):
        digest = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")
        # dau +-1 tu bit cao tranh hai token va cham chieu cong don thanh mot hang
        vector[digest % dims] += 1.0 if (digest >> 63) & 1 else -1.0
    return l2_normalize(vector)
