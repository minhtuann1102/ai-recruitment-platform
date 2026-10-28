"""Ghi seed job_db theo contract (spec 009 T045, FR-018..FR-021, research R10, bang Mapping data-model.md).

Moi cong ty -> mot Employer seed (`users` role Employer + `company_profiles`) trong user_db, email
`seed-<slug cong ty>@seed.ai-recruit.test`; da co theo email thi dung lai. Posting vao job_db, khoa idempotent
`(employer_id, title, md5(description))` kiem trong DB. Ham `*_row` thuan de test offline; ham nhan `conn` chay trong
transaction cua lenh goi (moi DB mot transaction, user_db truoc). id / created_at / updated_at do seed sinh vi bang
MikroORM khong co default.
"""
import uuid
from datetime import date, datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .job_seed_selector import company_slug, posting_description
from .skill_dictionary import SkillDictionary

SEED_EMAIL_DOMAIN = "seed.ai-recruit.test"
EMPLOYER_ROLE = "Employer"
DEADLINE_FALLBACK_DAYS = 30

PasswordHashFn = Callable[[], str]  # T039: hash cua chuoi ngau nhien khong luu (FSD + DE chot)


def employer_email(company: str) -> str:
    return f"seed-{company_slug(company)}@{SEED_EMAIL_DOMAIN}"


def employer_rows(company: str, password_hash: str, now: datetime) -> Tuple[Dict, Dict]:
    """(users, company_profiles) cho Employer seed moi; khong co ten / lien he nguoi that (FR-021)."""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id, "email": employer_email(company), "password": password_hash, "role": EMPLOYER_ROLE,
        "email_verified": True, "created_at": now, "updated_at": now,
    }
    profile = {"id": str(uuid.uuid4()), "user_id": user_id, "company_name": company, "created_at": now, "updated_at": now}
    return user, profile


def _number(value) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _deadline(jd: Dict, today: date) -> date:
    if jd.get("deadline"):
        return date.fromisoformat(jd["deadline"])
    posted = date.fromisoformat(jd["date_posted"]) if jd.get("date_posted") else today
    return posted + timedelta(days=DEADLINE_FALLBACK_DAYS)


def posting_row(jd: Dict, employer_id: str, level_id: str, now: datetime) -> Dict:
    salary_min, salary_max = _number(jd.get("salary_min")), _number(jd.get("salary_max"))
    has_salary = salary_min is not None or salary_max is not None
    return {
        "employer_id": employer_id, "title": jd["title"].strip(), "description": posting_description(jd),
        "requirements": jd["sections"]["requirements"].strip(), "salary_min": salary_min, "salary_max": salary_max,
        "salary_currency": jd.get("salary_currency") if has_salary else None, "location": jd["city"],
        "work_type": jd["work_type"], "experience_level_id": level_id, "status": "open",
        "deadline": _deadline(jd, now.date()), "created_at": now, "updated_at": now,
    }


def _insert(cur, table: str, row: Dict) -> None:
    columns = ", ".join(row)
    cur.execute(f"INSERT INTO {table} ({columns}) VALUES ({', '.join(['%s'] * len(row))})", tuple(row.values()))


def load_levels(job_conn) -> Dict[str, str]:
    with job_conn.cursor() as cur:
        cur.execute("SELECT name, id FROM experience_levels")
        return {name: str(level_id) for name, level_id in cur.fetchall()}


def ensure_employers(user_conn, companies: Iterable[str], password_hash: PasswordHashFn, now: datetime) -> Dict[str, str]:
    """{cong ty: id Employer}; cong ty cung slug dung chung Employer, ten luu la ten dau tien theo thu tu sap xep."""
    ids: Dict[str, str] = {}
    by_email: Dict[str, str] = {}
    with user_conn.cursor() as cur:
        for company in sorted(set(companies)):
            email = employer_email(company)
            if email not in by_email:
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                found = cur.fetchone()
                if found:
                    by_email[email] = str(found[0])
                else:
                    user, profile = employer_rows(company, password_hash(), now)
                    _insert(cur, "users", user)
                    _insert(cur, "company_profiles", profile)
                    by_email[email] = user["id"]
            ids[company] = by_email[email]
    return ids


def ensure_skills(job_conn, slugs: Iterable[str], dictionary: SkillDictionary, now: datetime) -> Dict[str, str]:
    """{slug danh muc: id trong job_db.skills}, moi slug deu co id. Tra theo slug truoc; khong co thi tra theo ten
    (job-service co the da co ky nang cung ten khac slug, `name` UNIQUE theo contract) va dung lai; khong co nua moi
    them tu danh muc. Kiem truoc khi them nen chay lai khong tao ban trung, ke ca khi `slug` khong co UNIQUE."""
    slugs = sorted(set(slugs))
    with job_conn.cursor() as cur:
        cur.execute("SELECT slug, id FROM skills WHERE slug = ANY(%s)", (slugs,))
        ids = {slug: str(skill_id) for slug, skill_id in cur.fetchall()}
        for slug in (s for s in slugs if s not in ids):
            skill = dictionary.skills[slug]
            cur.execute("SELECT id FROM skills WHERE lower(name) = lower(%s)", (skill.name,))
            found = cur.fetchone()
            if found:
                ids[slug] = str(found[0])
                continue
            ids[slug] = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO skills (id, name, slug, category, created_at) VALUES (%s, %s, %s, %s, %s)",
                (ids[slug], skill.name, slug, skill.category, now),
            )
    return ids


def insert_postings(job_conn, items: List[Tuple[Dict, Dict]], skill_ids: Dict[str, str]) -> List[Dict]:
    """items = [(jd, posting_row)]; tra dong manifest {jd_id, posting_id, employer_id, synthetic, inserted}."""
    manifest = []
    with job_conn.cursor() as cur:
        for jd, row in items:
            cur.execute(
                "SELECT id FROM job_postings WHERE employer_id = %s AND title = %s AND md5(description) = md5(%s)",
                (row["employer_id"], row["title"], row["description"]),
            )
            found = cur.fetchone()
            posting_id = str(found[0]) if found else str(uuid.uuid4())
            if not found:
                _insert(cur, "job_postings", {"id": posting_id, **row})
                for slug in dict.fromkeys(jd["skills"]):
                    cur.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (%s, %s)", (posting_id, skill_ids[slug]))
            manifest.append({
                "jd_id": jd["jd_id"], "posting_id": posting_id, "employer_id": row["employer_id"],
                "synthetic": bool(jd.get("synthetic")), "inserted": not found,
            })
    return manifest


def seed_employer_ids(user_conn) -> List[str]:
    with user_conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email LIKE %s", (f"%@{SEED_EMAIL_DOMAIN}",))
        return [str(row[0]) for row in cur.fetchall()]


def clean_postings(job_conn, employer_ids: List[str]) -> int:
    """Xoa job_skills + job_postings cua Employer seed; tra so posting da xoa."""
    with job_conn.cursor() as cur:
        cur.execute(
            "DELETE FROM job_skills WHERE job_id IN (SELECT id FROM job_postings WHERE employer_id = ANY(%s::uuid[]))",
            (employer_ids,),
        )
        cur.execute("DELETE FROM job_postings WHERE employer_id = ANY(%s::uuid[])", (employer_ids,))
        return cur.rowcount


def clean_employers(user_conn, employer_ids: List[str]) -> int:
    """Xoa company_profiles + users cua Employer seed (chi email mien seed); tra so Employer da xoa."""
    with user_conn.cursor() as cur:
        cur.execute("DELETE FROM company_profiles WHERE user_id = ANY(%s::uuid[])", (employer_ids,))
        cur.execute(
            "DELETE FROM users WHERE id = ANY(%s::uuid[]) AND email LIKE %s", (employer_ids, f"%@{SEED_EMAIL_DOMAIN}")
        )
        return cur.rowcount
