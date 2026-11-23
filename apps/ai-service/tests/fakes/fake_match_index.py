"""Fake dung chung cho test chi muc JD (017): ket noi ai_db gia, dong ho gia, dong (embedding::text, metadata)."""
from datetime import datetime, timezone

from app.matching.hash_embedder import EMBEDDING_DIMS
from app.matching.job_index import JobIndex
from app.matching.settings import load_match_settings

DSN = "postgresql://aie_reader:S3CRET@db.example:5432/ai_db"
ENV = {"AI_DB_URL": DSN, "MATCH_INDEX_REFRESH_S": "300", "AI_DB_CONNECT_TIMEOUT_S": "4"}


def vec_text(*head: float) -> str:
    """embedding::text cua pgvector: '[x,y,...]' du 1536 so."""
    return "[" + ",".join(str(x) for x in (*head, *([0] * (EMBEDDING_DIMS - len(head))))) + "]"


def meta(jd_id="jd:1", **kw):
    base = {"dataset": "jd-match", "chunk_type": "jd_match_summary", "jd_id": jd_id, "title": "Backend Developer (Java)",
            "group": "backend", "level": "Mid", "deadline": "2030-12-01", "skills": ["java", "kafka"],
            "synthetic": False}
    base.update(kw)
    return base


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    async def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self, rows, gate=None):
        self.rows, self.gate, self.executed, self.closed = rows, gate, [], False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.closed = True
        return False

    async def execute(self, sql, params):
        self.executed.append((sql, params))
        if self.gate is not None:
            await self.gate.wait()
        return _Cursor(self.rows)


class FakeDb:
    """connect gia: dem so lan mo, ghi tham so ket noi; rows doi duoc giua cac lan nap; fail=True thi nem loi mang."""

    def __init__(self, rows, gate=None):
        self.rows, self.gate, self.fail = rows, gate, False
        self.calls, self.conns, self.seen = 0, [], []

    async def __call__(self, dsn, **kw):
        self.calls += 1
        self.seen.append((dsn, kw))
        if self.fail:
            raise OSError("khong toi duoc db.example")
        conn = _Conn(self.rows, self.gate)
        self.conns.append(conn)
        return conn


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make_index(db, env=None, clock=None, **kwargs):
    """JobIndex voi ket noi gia, dong ho gia (Clock) va gio nap co dinh; kwargs di thang vao JobIndex."""
    clock = clock or Clock()
    return JobIndex(load_match_settings({**ENV, **(env or {})}), connect=db, monotonic=clock,
                    now=lambda: datetime(2026, 11, 22, 9, 0, 0, tzinfo=timezone.utc), **kwargs), clock
