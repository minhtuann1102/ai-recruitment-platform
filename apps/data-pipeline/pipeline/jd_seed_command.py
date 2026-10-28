"""Lenh seed-jobs [--count 200] [--clean] (spec 009 US4, contracts/pipeline-cli-jd.md).

Preflight schema user_db + job_db -> chon posting tu JD_NORMALIZED_PATH (crawl truoc) -> Employer seed (user_db, commit
truoc) -> posting + job_skills (job_db) -> manifest JD_SEED_MANIFEST_PATH. `--clean` chi xoa du lieu cua Employer seed.
Ma thoat: 0; 1 chua co JD chuan hoa / thieu JD dat dieu kien; 2 thieu USER_DB_URL / JOB_DB_URL, khong ket noi duoc,
schema thieu / khac contract, hoac chua chot cach tao password Employer seed (T039).
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional

import psycopg

from .jd_normalizer import LEVELS
from .jd_process_command import write_jsonl
from .job_db_seed_preflight import schema_problems
from .job_db_seed_writer import (
    PasswordHashFn, clean_employers, clean_postings, ensure_employers, ensure_skills, insert_postings, load_levels,
    posting_row, seed_employer_ids,
)
from .job_seed_selector import FLOOR_AXES, select_postings
from .settings import (
    JD_NORMALIZED_PATH, JD_SEED_MANIFEST_PATH, SKILL_DICTIONARY_PATH, ConfigError, require_seed_settings,
)
from .skill_dictionary import SkillDictionaryError, load_skill_dictionary

EXIT_OK, EXIT_INPUT_ERROR, EXIT_PREFLIGHT_ERROR = 0, 1, 2

# T039 (DE + FSD) chua chot cach tao password "bcrypt cua chuoi ngau nhien khong luu" (FR-021): None -> seed thoat 2
# truoc moi lenh ghi. Chot xong thi gan ham tra hash moi lan goi.
SEED_PASSWORD_HASH: Optional[PasswordHashFn] = None


def read_normalized() -> List[Dict]:
    if not JD_NORMALIZED_PATH.exists():
        raise FileNotFoundError(f"chua co {JD_NORMALIZED_PATH}, chay process-jd truoc")
    with JD_NORMALIZED_PATH.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _clean(user_conn, job_conn) -> int:
    employer_ids = seed_employer_ids(user_conn)
    postings = clean_postings(job_conn, employer_ids)
    job_conn.commit()
    employers = clean_employers(user_conn, employer_ids)
    user_conn.commit()
    print(f"da xoa {postings} posting, {employers} Employer seed")
    return EXIT_OK


def _print_summary(selected: List[Dict], manifest: List[Dict], employers: int) -> None:
    inserted = sum(1 for row in manifest if row["inserted"])
    synthetic = sum(1 for row in manifest if row["synthetic"])
    print(f"posting moi: {inserted}, da co: {len(manifest) - inserted}, synthetic: {synthetic}, Employer seed: {employers}")
    for axis, _ in FLOOR_AXES:
        counts = Counter(jd.get(axis) for jd in selected)
        print(f"  {axis}: " + ", ".join(f"{value} {n}" for value, n in sorted(counts.items(), key=lambda kv: -kv[1])))


def seed_jobs(args: argparse.Namespace, user_conn, job_conn, password_hash: Optional[PasswordHashFn], now: datetime) -> int:
    problems = schema_problems({"user_db": user_conn, "job_db": job_conn})
    if problems:
        print("schema khong khop contract, khong ghi:\n  " + "\n  ".join(problems), file=sys.stderr)
        return EXIT_PREFLIGHT_ERROR
    if args.clean:
        return _clean(user_conn, job_conn)
    if password_hash is None:
        print("chua chot cach tao password Employer seed (T039, DE + FSD), khong ghi", file=sys.stderr)
        return EXIT_PREFLIGHT_ERROR

    levels = load_levels(job_conn)
    absent = [level for level in LEVELS if level not in levels]
    if absent:
        print(f"experience_levels thieu {', '.join(absent)}: JD cap nay khong duoc chon")
    try:
        dictionary = load_skill_dictionary(SKILL_DICTIONARY_PATH)
        selection = select_postings(read_normalized(), levels, args.count)
    except (OSError, ValueError, SkillDictionaryError) as exc:
        print(f"loi doc du lieu: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    if selection.errors:
        print("khong du JD dat dieu kien seed:\n  " + "\n  ".join(selection.errors), file=sys.stderr)
        return EXIT_INPUT_ERROR
    for warning in selection.warnings:
        print(f"canh bao: {warning}")

    employer_ids = ensure_employers(user_conn, {jd["company"] for jd in selection.selected}, password_hash, now)
    user_conn.commit()  # user_db truoc: chay lai sau loi job_db se dung lai Employer theo email
    slugs = {slug for jd in selection.selected for slug in jd["skills"]}
    skill_ids = ensure_skills(job_conn, slugs, dictionary, now)
    if slugs - set(skill_ids):
        print(f"canh bao: skills trung ten khac slug, khong gan: {', '.join(sorted(slugs - set(skill_ids)))}")
    items = [
        (jd, posting_row(jd, employer_ids[jd["company"]], levels[jd["level"]], now)) for jd in selection.selected
    ]
    manifest = insert_postings(job_conn, items, skill_ids)
    job_conn.commit()
    write_jsonl(JD_SEED_MANIFEST_PATH, manifest)
    _print_summary(selection.selected, manifest, len(set(employer_ids.values())))
    print(f"-> {JD_SEED_MANIFEST_PATH}")
    return EXIT_OK


def run_seed_jobs(args: argparse.Namespace) -> int:
    try:
        settings = require_seed_settings()
        with psycopg.connect(settings.user_db_url) as user_conn, psycopg.connect(settings.job_db_url) as job_conn:
            return seed_jobs(args, user_conn, job_conn, SEED_PASSWORD_HASH, datetime.now(timezone.utc))
    except (ConfigError, psycopg.OperationalError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT_ERROR
