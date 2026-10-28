"""Ham thuan cua seed writer (spec 009 T046, FR-018, FR-021, bang Mapping data-model.md): khong DB."""
from datetime import date, datetime, timezone

from pipeline.job_db_seed_writer import SEED_EMAIL_DOMAIN, employer_email, employer_rows, posting_row
from pipeline.job_seed_selector import company_slug

NOW = datetime(2026, 10, 28, 7, 0, tzinfo=timezone.utc)


def _jd(**overrides):
    jd = {
        "jd_id": "itviec:1", "title": " Backend Developer ", "company": "Công Ty CP Đất Việt", "city": "Hà Nội",
        "work_type": "hybrid", "level": "Mid", "skills": ["python"], "synthetic": False,
        "salary_min": 20000000, "salary_max": 30000000, "salary_currency": "VND",
        "date_posted": "2026-10-20", "deadline": "2026-11-30",
        "sections": {
            "summary": "Tom tat", "description": "Mo ta", "responsibilities": "Viet API", "benefits": "Thuong",
            "requirements": " 2 nam Python ",
        },
    }
    jd.update(overrides)
    return jd


def test_posting_row_maps_contract_columns():
    row = posting_row(_jd(), "emp-1", "lvl-mid", NOW)
    assert row["description"] == "Tom tat\n\nMo ta\n\nViet API\n\nThuong"
    assert row["title"] == "Backend Developer" and row["requirements"] == "2 nam Python"
    assert (row["location"], row["work_type"], row["status"]) == ("Hà Nội", "hybrid", "open")
    assert (row["employer_id"], row["experience_level_id"]) == ("emp-1", "lvl-mid")
    assert (row["salary_min"], row["salary_max"], row["salary_currency"]) == (20000000, 30000000, "VND")
    assert row["deadline"] == date(2026, 11, 30) and row["created_at"] == row["updated_at"] == NOW


def test_text_salary_becomes_null_and_drops_currency():
    row = posting_row(_jd(salary_min="Thỏa thuận", salary_max=None), "e", "l", NOW)
    assert (row["salary_min"], row["salary_max"], row["salary_currency"]) == (None, None, None)


def test_one_numeric_salary_bound_keeps_currency():
    row = posting_row(_jd(salary_min=None, salary_max=1500, salary_currency="USD"), "e", "l", NOW)
    assert (row["salary_min"], row["salary_max"], row["salary_currency"]) == (None, 1500, "USD")


def test_deadline_falls_back_to_date_posted_plus_30_days_then_today():
    assert posting_row(_jd(deadline=None), "e", "l", NOW)["deadline"] == date(2026, 11, 19)
    assert posting_row(_jd(deadline=None, date_posted=None), "e", "l", NOW)["deadline"] == date(2026, 11, 27)


def test_employer_email_is_company_slug_in_seed_domain():
    assert company_slug("Công Ty CP Đất Việt") == "cong-ty-cp-dat-viet"
    assert employer_email("CÔNG TY CP ĐẤT VIỆT") == employer_email("Công Ty CP Đất Việt")
    assert employer_email("Công Ty CP Đất Việt") == f"seed-cong-ty-cp-dat-viet@{SEED_EMAIL_DOMAIN}"
    long_email = employer_email("Công ty TNHH " + "Giải pháp phần mềm " * 6)
    assert len(long_email.split("@")[0]) <= 64 and not long_email.split("@")[0].endswith("-")
    assert employer_email("!!!") == f"seed-company@{SEED_EMAIL_DOMAIN}"


def test_employer_rows_have_no_person_data_and_link_profile():
    user, profile = employer_rows("Công Ty CP Đất Việt", "$2b$12$hash", NOW)
    assert user["role"] == "Employer" and user["email_verified"] is True and user["password"] == "$2b$12$hash"
    assert set(user) == {"id", "email", "password", "role", "email_verified", "created_at", "updated_at"}
    assert profile["user_id"] == user["id"] and profile["company_name"] == "Công Ty CP Đất Việt"
