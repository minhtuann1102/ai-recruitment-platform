"""Cache cuc bo cua thi nghiem embedding: evals/.cache/ (gitignore `*`). Noi dung crawl (corpus.jsonl) KHONG bao gio commit.

- corpus.jsonl: kho interview_qa doc tu ai_db (id, content, content_hash, qa_id, chunk_type, topic_id, category, difficulty).
- vec-<model>-<rev12>.npz: vector chunk khoa theo content_hash; kem `config` (model, revision, tien to, max_seq_length...)
  khac config thi bo cache cu. Ghi tung phan duoc (bge-m3 chay lau, chay lai thi tiep tuc).
- qvec-<model>-<rev12>.json: vector truy van khoa theo sha1(van ban). rewrites.json: ban viet lai LLM, tao MOT lan.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from app.rag.models import Chunk

CACHE = Path(__file__).parent / ".cache"


def cache_dir() -> Path:
    CACHE.mkdir(exist_ok=True)
    guard = CACHE / ".gitignore"
    if not guard.exists():
        guard.write_text("*\n", encoding="utf-8")
    return CACHE


def write_json(name: str, obj: Any) -> None:
    path = cache_dir() / name
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_json(name: str, default: Any = None) -> Any:
    path = cache_dir() / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def text_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def save_corpus(rows: Sequence[Dict]) -> None:
    path = cache_dir() / "corpus.jsonl"
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_corpus() -> List[Dict]:
    path = cache_dir() / "corpus.jsonl"
    if not path.exists():
        raise SystemExit("Chua co corpus.jsonl: chay `load-corpus` truoc")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def chunks_from_rows(rows: Sequence[Dict]) -> List[Chunk]:
    """Chunk khong mang noi dung (chi can dedup_key = qa_id cho duong tim); thu tu = thu tu hang ma tran vector."""
    return [Chunk(id=r["id"], content="", source_type="interview_qa", topic_id=r["topic_id"], category=r["category"],
                  difficulty=r["difficulty"], qa_id=r["qa_id"], chunk_type=r["chunk_type"]) for r in rows]


class VectorStore:
    """Vector theo content_hash, luu np.savez. `config` phai khop thi cache cu moi dung duoc."""

    def __init__(self, name: str, config: Dict):
        self.path, self.config = cache_dir() / f"vec-{name}.npz", config
        self.hashes: List[str] = []
        self.vecs: Optional[np.ndarray] = None
        self.meta: Dict = {}
        if self.path.exists():
            z = np.load(self.path, allow_pickle=False)
            if json.loads(str(z["config"])) == config:
                self.hashes, self.vecs = [str(h) for h in z["hashes"]], z["vecs"]
                self.meta = json.loads(str(z["meta"]))

    def missing(self, hashes: Sequence[str]) -> List[str]:
        have = set(self.hashes)
        return [h for h in hashes if h not in have]

    def add(self, hashes: Sequence[str], vecs: np.ndarray) -> None:
        vecs = np.asarray(vecs, dtype=np.float32)
        self.vecs = vecs if self.vecs is None else np.vstack([self.vecs, vecs])
        self.hashes.extend(hashes)

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp.npz")
        np.savez(tmp, hashes=np.array(self.hashes, dtype="U40"), vecs=self.vecs, config=json.dumps(self.config),
                 meta=json.dumps(self.meta))
        os.replace(tmp, self.path)

    def matrix(self, hashes: Sequence[str]) -> np.ndarray:
        """Ma tran theo thu tu `hashes`; thieu hash nao thi KeyError (khong dien 0)."""
        pos = {h: i for i, h in enumerate(self.hashes)}
        return self.vecs[[pos[h] for h in hashes]]
