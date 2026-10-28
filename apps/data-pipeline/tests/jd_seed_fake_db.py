"""DB gia cho test seed-jobs (spec 009 US4): tra loi dung cac cau SQL seed dung, ghi thu tu insert / commit vao `log`.

Khong phai Postgres: chi du de kiem luong lenh (preflight, idempotent, thu tu commit, --clean). Cau SQL la -> loi ngay
de test bao khi writer doi SQL ma fake chua theo.
"""
import re
from typing import Callable, Dict, List

from pipeline.job_db_seed_preflight import EXPECTED_COLUMNS

_INSERT_RE = re.compile(r"INSERT INTO (\w+) \(([^)]*)\) VALUES")
LEVEL_NAMES = ("Intern", "Junior", "Mid", "Senior", "Lead", "Manager")


def contract_schema() -> Dict[str, Dict[str, Dict[str, bool]]]:
    """Schema dung contract nhu migration MikroORM: id / created_at khong default (seed ghi), cot khac co default."""
    schema = {db: {t: {c: c in ("id", "created_at", "updated_at") for c in cols} for t, cols in tables.items()}
              for db, tables in EXPECTED_COLUMNS.items()}
    schema["user_db"]["users"]["is_active"] = False  # NOT NULL default true
    schema["job_db"]["experience_levels"]["sort_order"] = True  # NOT NULL khong default, seed chi doc bang nay
    return schema


class FakeDb:
    def __init__(self, name: str, schema: Dict[str, Dict[str, bool]], log: List[str]):
        self.name, self.schema, self.log = name, schema, log
        self.tables: Dict[str, List[Dict]] = {table: [] for table in schema}
        if "experience_levels" in self.tables:
            self.tables["experience_levels"] = [{"id": f"lvl-{n}", "name": n} for n in LEVEL_NAMES]

    def cursor(self) -> "FakeCursor":
        return FakeCursor(self)

    def commit(self) -> None:
        self.log.append(f"commit {self.name}")


class FakeCursor:
    def __init__(self, db: FakeDb):
        self.db, self.rows, self.rowcount = db, [], 0

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def fetchall(self) -> List[tuple]:
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def _select(self, table: str, keep: Callable[[Dict], bool], *columns: str) -> None:
        self.rows = [tuple(r[c] for c in columns) for r in self.db.tables[table] if keep(r)]

    def _delete(self, table: str, drop: Callable[[Dict], bool]) -> None:
        before = self.db.tables[table]
        self.db.tables[table] = [r for r in before if not drop(r)]
        self.rowcount = len(before) - len(self.db.tables[table])
        self.db.log.append(f"delete {self.db.name}.{table}")

    def execute(self, sql: str, params=()) -> None:
        sql, t, self.rows = " ".join(sql.split()), self.db.tables, []
        insert = _INSERT_RE.match(sql)
        if "information_schema.columns" in sql:
            self.rows = [(tb, c, req) for tb, cols in self.db.schema.items() if tb in params[0] for c, req in cols.items()]
        elif insert:
            self.db.log.append(f"insert {self.db.name}.{insert.group(1)}")
            t[insert.group(1)].append(dict(zip((c.strip() for c in insert.group(2).split(",")), params)))
        elif sql.startswith("SELECT name, id FROM experience_levels"):
            self._select("experience_levels", lambda r: True, "name", "id")
        elif sql.startswith("SELECT id FROM users WHERE email = "):
            self._select("users", lambda r: r["email"] == params[0], "id")
        elif sql.startswith("SELECT id FROM users WHERE email LIKE"):
            self._select("users", lambda r: r["email"].endswith(params[0].lstrip("%")), "id")
        elif sql.startswith("SELECT slug, id FROM skills"):
            self._select("skills", lambda r: r["slug"] in params[0], "slug", "id")
        elif sql.startswith("SELECT id FROM skills WHERE lower(name)"):
            self._select("skills", lambda r: r["name"].lower() == params[0].lower(), "id")
        elif sql.startswith("SELECT id FROM job_postings WHERE employer_id"):
            self._select("job_postings", lambda r: (r["employer_id"], r["title"], r["description"]) == params, "id")
        elif sql.startswith("DELETE FROM job_skills"):
            seed_jobs = {r["id"] for r in t["job_postings"] if r["employer_id"] in params[0]}
            self._delete("job_skills", lambda r: r["job_id"] in seed_jobs)
        elif sql.startswith("DELETE FROM job_postings"):
            self._delete("job_postings", lambda r: r["employer_id"] in params[0])
        elif sql.startswith("DELETE FROM company_profiles"):
            self._delete("company_profiles", lambda r: r["user_id"] in params[0])
        elif sql.startswith("DELETE FROM users"):
            self._delete("users", lambda r: r["id"] in params[0] and r["email"].endswith(params[1].lstrip("%")))
        else:
            raise AssertionError(f"fake DB chua ho tro SQL: {sql}")
