"""Ket noi DB gia (trong bo nho) + embedder gia cho test index-jd-match (spec 017). Khong mang, khong DB that.

FakeDb ap dung THAM SO cua SQL (source_type, dataset, hash) va chi nhan dung nhung cau SQL da biet: cac cau co pham vi
(SELECT model, DELETE --rebuild, DELETE don cua writer) phai khop CHINH XAC chuoi viet tay duoi day (da chuan hoa khoang
trang), khong import tu module. Code doi WHERE (vd AND -> OR) thi fake nem AssertionError thay vi xanh gia.
"""
from typing import Dict, List, Optional, Sequence

EXPECTED_MODELS_SQL = (
    "SELECT DISTINCT embedding_model FROM knowledge_chunks WHERE source_type = %s AND metadata->>'dataset' = %s")
EXPECTED_REBUILD_DELETE_SQL = "DELETE FROM knowledge_chunks WHERE source_type = %s AND metadata->>'dataset' = %s"
EXPECTED_CLEANUP_DELETE_SQL = (
    "DELETE FROM knowledge_chunks WHERE source_type = %s AND metadata->>'dataset' = %s AND NOT (content_hash = ANY(%s))")


def make_jd(jd_id="demo:1", **overrides):
    """JD chuan hoa theo 009 jd-record-formats (du lieu bia)."""
    jd = {
        "jd_id": jd_id,
        "title": "Backend Developer (Java)",
        "company": "Cong ty Sao Mai",
        "skills": ["java", "spring-boot"],
        "skills_unknown": [],
        "group": "backend",
        "level": "Mid",
        "deadline": "2026-12-01",
        "sections": {
            "summary": "Backend Developer (Java)\nCông ty: Sao Mai\nCấp bậc: Mid\nKỹ năng: Java, Spring Boot",
            "description": "MOTA: xây dựng API thanh toán.",
            "responsibilities": "CONGVIEC: viết dịch vụ đặt lịch.",
            "requirements": "YEUCAU: 3 năm Java, hiểu SQL.",
            "benefits": "PHUCLOI: thưởng tháng 13.",
        },
        "language": "vi",
        "synthetic": False,
    }
    jd.update(overrides)
    return jd


class FakeDb:
    def __init__(self):
        self.rows: Dict[str, Dict] = {}  # content_hash -> {source_type, dataset, model, content, metadata}
        self.log: List[tuple] = []  # (loai, tham so) theo thu tu thuc thi
        self.commits = 0

    def seed(self, content_hash: str, source_type: str, dataset: str, model: str = "text-embedding-3-small") -> None:
        self.rows[content_hash] = {"source_type": source_type, "dataset": dataset, "model": model, "content": "seed",
                                   "metadata": {"dataset": dataset}}

    def kinds(self, kind: str) -> List[tuple]:
        return [params for name, params in self.log if name == kind]

    def of(self, source_type: str, dataset: str) -> Dict[str, Dict]:
        return {h: r for h, r in self.rows.items() if (r["source_type"], r["dataset"]) == (source_type, dataset)}

    def cursor(self):
        return _FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeCursor:
    def __init__(self, db: FakeDb):
        self.db, self.rowcount, self._rows = db, 0, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def execute(self, sql: str, params: Sequence = ()) -> None:
        sql, db = " ".join(sql.split()), self.db
        self._rows, self.rowcount = [], 0
        if sql.startswith("SELECT 1 FROM pg_extension"):
            self._rows = [(1,)]
        elif sql.startswith("SELECT to_regclass"):
            self._rows = [("knowledge_chunks",)]
        elif sql == EXPECTED_MODELS_SQL:
            db.log.append(("models", tuple(params)))
            self._rows = [(m,) for m in sorted({r["model"] for r in db.of(*params).values()})]
        elif sql.startswith("SELECT content_hash, metadata->>'dataset'"):
            self._rows = [(h, db.rows[h]["dataset"]) for h in params[0] if h in db.rows]
        elif sql.startswith("INSERT INTO knowledge_chunks"):
            content, chash, _vector, model, source_type, _cat, _diff, _topic, _lang, meta = params
            db.log.append(("insert", (chash,)))
            if chash not in db.rows:  # ON CONFLICT (content_hash) DO NOTHING
                db.rows[chash] = {"source_type": source_type, "dataset": meta.obj["dataset"], "model": model,
                                  "content": content, "metadata": meta.obj}
                self.rowcount = 1
        elif sql.startswith("UPDATE knowledge_chunks"):
            content, _cat, _diff, _topic, _lang, meta, chash, dataset = params
            db.log.append(("update", (chash,)))
            if chash in db.rows and db.rows[chash]["dataset"] == dataset:
                db.rows[chash].update(content=content, metadata=meta.obj)
                self.rowcount = 1
        elif sql == EXPECTED_CLEANUP_DELETE_SQL:
            source_type, dataset, keep = params  # don cung dataset sau khi ghi (writer)
            doomed = [h for h in db.of(source_type, dataset) if h not in keep]
            db.log.append(("delete_cleanup", (source_type, dataset)))
            self._drop(doomed)
        elif sql == EXPECTED_REBUILD_DELETE_SQL:
            source_type, dataset = params  # --rebuild: ca dataset
            db.log.append(("delete_dataset", (source_type, dataset)))
            self._drop(list(db.of(source_type, dataset)))
        else:
            raise AssertionError(f"SQL la hoac da doi pham vi, fake DB khong nhan: {sql}")

    def _drop(self, hashes: List[str]) -> None:
        for h in hashes:
            del self.db.rows[h]
        self.rowcount = len(hashes)


class FakeEmbedder:
    """Giong EmbeddingClient: embed / probe / total_tokens. fail_embed=True: embed ra loi (probe van qua)."""

    def __init__(self, fail_embed: bool = False, fail_probe: Optional[Exception] = None, tokens_per_text: int = 3):
        self.total_tokens, self.probe_calls, self.embed_calls = 0, 0, []
        self._fail_embed, self._fail_probe, self._tokens = fail_embed, fail_probe, tokens_per_text

    def probe(self) -> None:
        self.probe_calls += 1
        if self._fail_probe:
            raise self._fail_probe

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if self._fail_embed:
            raise RuntimeError("provider down")
        self.embed_calls.append(list(texts))
        self.total_tokens += self._tokens * len(texts)
        return [[0.1, 0.2] for _ in texts]
