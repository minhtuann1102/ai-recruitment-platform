"""Preflight schema seed-jobs (spec 009 T044, FR-019): ham thuan, khong DB."""
from pipeline.job_db_seed_preflight import EXPECTED_COLUMNS, missing_columns, unfilled_required_columns


def _actual(db):
    """Schema dung contract: moi cot seed can deu co, khong cot nao bat buoc ngoai danh sach."""
    return {table: {column: False for column in columns} for table, columns in EXPECTED_COLUMNS[db].items()}


def test_matching_schema_has_no_problems():
    for db, expected in EXPECTED_COLUMNS.items():
        assert missing_columns(expected, _actual(db)) == []
        assert unfilled_required_columns(expected, _actual(db)) == []


def test_missing_company_name_column_is_reported():
    actual = _actual("user_db")
    del actual["company_profiles"]["company_name"]
    assert missing_columns(EXPECTED_COLUMNS["user_db"], actual) == ["company_profiles.company_name"]


def test_missing_job_skills_table_is_reported_once():
    actual = _actual("job_db")
    del actual["job_skills"]
    assert missing_columns(EXPECTED_COLUMNS["job_db"], actual) == ["bang job_skills"]


def test_required_column_without_default_outside_mapping_is_reported():
    actual = _actual("user_db")
    actual["users"]["is_2fa_enabled"] = False  # NOT NULL default false: ghi duoc
    actual["company_profiles"]["company_size"] = True  # NOT NULL khong default: seed khong co gia tri
    assert unfilled_required_columns(EXPECTED_COLUMNS["user_db"], actual) == ["company_profiles.company_size"]


def test_required_columns_seed_writes_are_not_reported():
    actual = _actual("user_db")
    actual["users"]["id"] = actual["users"]["created_at"] = True  # MikroORM: khong default, seed tu ghi
    assert unfilled_required_columns(EXPECTED_COLUMNS["user_db"], actual) == []
