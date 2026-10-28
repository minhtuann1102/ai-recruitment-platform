"""Preflight schema cho seed-jobs (spec 009 T043, FR-019, research R10).

Doi chieu information_schema.columns cua user_db va job_db voi cac cot seed ghi / doc (bang Mapping cua data-model.md
spec 009). Hai loai loi, deu dung truoc moi lenh ghi (lenh thoat 2); MUST NOT tao / sua bang:
- thieu bang hoac cot seed can;
- cot NOT NULL khong co default ma seed khong ghi (khong co nguon gia tri, INSERT se loi giua chung).
Bang cua MikroORM khong co default cho id / created_at / updated_at (app tu sinh), nen seed tu ghi cac cot nay.
"""
from typing import Dict, Iterable, List, Tuple

# Cot seed ghi hoac doc, theo DB -> bang
EXPECTED_COLUMNS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "user_db": {
        "users": ("id", "email", "password", "role", "email_verified", "created_at", "updated_at"),
        "company_profiles": ("id", "user_id", "company_name", "created_at", "updated_at"),
    },
    "job_db": {
        "job_postings": (
            "id", "employer_id", "title", "description", "requirements", "salary_min", "salary_max", "salary_currency",
            "location", "work_type", "experience_level_id", "status", "deadline", "created_at", "updated_at",
        ),
        "job_skills": ("job_id", "skill_id"),
        "skills": ("id", "name", "slug", "category", "created_at"),
        "experience_levels": ("id", "name"),
    },
}
# Bang seed chi doc: chi kiem co cot, khong kiem cot NOT NULL (vd experience_levels.sort_order cua migration that)
READ_ONLY_TABLES = frozenset({"experience_levels"})

# bang -> {cot: True neu NOT NULL va khong co default}
ActualColumns = Dict[str, Dict[str, bool]]

_COLUMNS_SQL = """
SELECT table_name, column_name,
       is_nullable = 'NO' AND column_default IS NULL AND is_identity = 'NO' AND is_generated = 'NEVER' AS required
FROM information_schema.columns
WHERE table_schema = current_schema() AND table_name = ANY(%s)
"""


def missing_columns(expected: Dict[str, Iterable[str]], actual: ActualColumns) -> List[str]:
    """Bang / cot seed can ma schema that khong co, vd 'bang job_skills', 'company_profiles.company_name'."""
    problems = []
    for table, columns in expected.items():
        if table not in actual:
            problems.append(f"bang {table}")
            continue
        problems.extend(f"{table}.{column}" for column in columns if column not in actual[table])
    return problems


def unfilled_required_columns(expected: Dict[str, Iterable[str]], actual: ActualColumns) -> List[str]:
    """Cot NOT NULL khong default cua bang seed ghi ma seed khong co gia tri cho no."""
    problems = []
    for table, columns in expected.items():
        written = set(columns)
        problems.extend(
            f"{table}.{column}" for column, required in sorted(actual.get(table, {}).items())
            if required and column not in written
        )
    return problems


def read_columns(conn, tables: Iterable[str]) -> ActualColumns:
    actual: ActualColumns = {}
    with conn.cursor() as cur:
        cur.execute(_COLUMNS_SQL, (list(tables),))
        for table, column, required in cur.fetchall():
            actual.setdefault(table, {})[column] = bool(required)
    return actual


def db_problems(db: str, actual: ActualColumns) -> List[str]:
    """Loi schema cua mot DB so voi EXPECTED_COLUMNS[db]; cot bat buoc chi kiem o bang seed ghi."""
    expected = EXPECTED_COLUMNS[db]
    written = {table: columns for table, columns in expected.items() if table not in READ_ONLY_TABLES}
    return [f"{db}: thieu {name}" for name in missing_columns(expected, actual)] + [
        f"{db}: {name} NOT NULL khong co default, seed khong co gia tri"
        for name in unfilled_required_columns(written, actual)
    ]


def schema_problems(connections: Dict[str, object]) -> List[str]:
    """Loi schema cua moi DB trong EXPECTED_COLUMNS, `connections` = {'user_db': conn, 'job_db': conn}; rong = ghi duoc."""
    problems = []
    for db, expected in EXPECTED_COLUMNS.items():
        problems.extend(db_problems(db, read_columns(connections[db], expected)))
    return problems
