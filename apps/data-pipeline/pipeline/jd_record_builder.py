"""Raw JD -> Normalized JD (spec 009 research R7, FR-008, FR-010, FR-011, FR-028; data-model.md).

Mot ban ghi: lam sach (text_cleaning.clean_text) + xoa PII (jd_pii) -> ky nang = canonical(skills_raw) ∪
find_in_text(tieu de + mo ta) -> loc IT -> chuan hoa truong -> section. Loai voi ly do:
- missing_field: thieu truong bat buoc, hoac mo ta sau lam sach ngan hon MIN_DESCRIPTION_CHARS (mo ta coi nhu thieu);
- not_it: khong qua jd_it_filter.is_it_job (FR-028, Clarifications 2026-10-28).
Dedup (duplicate) lam o jd_record_dedup.py.
"""
import hashlib
import unicodedata
from typing import Dict, List, Optional, Tuple

from .jd_city import normalize_city
from .jd_it_filter import is_it_job
from .jd_normalizer import detect_language, normalize_level, normalize_work_type
from .jd_pii import scrub_jd_pii
from .jd_salary import normalize_salary
from .jd_sections import build_summary, split_sections
from .skill_dictionary import SkillDictionary
from .text_cleaning import clean_text

REJECT_MISSING = "missing_field"
REJECT_NOT_IT = "not_it"
REJECT_DUPLICATE = "duplicate"
REJECT_REASONS = (REJECT_NOT_IT, REJECT_MISSING, REJECT_DUPLICATE)
REQUIRED_RAW_FIELDS = ("source", "source_job_id", "crawled_at", "title", "company", "description_text")
SYNTHETIC_SOURCE = "synthetic"
# Mo ta qua ngan khong du lam posting / chunk (topdev co tin chi ~180 ky tu)
MIN_DESCRIPTION_CHARS = 200
def is_synthetic(raw: Dict) -> bool:
    return bool(raw.get("synthetic")) or raw.get("source") == SYNTHETIC_SOURCE


def jd_id_of(raw: Dict) -> str:
    return f"{raw.get('source') or ''}:{raw.get('source_job_id') or ''}"


def _clean(value: object) -> str:
    return scrub_jd_pii(clean_text(value)) if isinstance(value, str) else ""


def content_hash(company: str, title: str, description: str) -> str:
    """SHA-256 cua 'cong ty | tieu de | mo ta' sau NFC, chu thuong, gop khoang trang (FR-013)."""
    joined = " | ".join(" ".join(unicodedata.normalize("NFC", part).lower().split()) for part in (company, title, description))
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _skill_names(raw: Dict) -> List[str]:
    values = raw.get("skills_raw")
    return [clean_text(v) for v in values if isinstance(v, str)] if isinstance(values, list) else []


def _strings(value: object) -> List[str]:
    if isinstance(value, str):
        return [value]
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def build_record(raw: Dict, dictionary: SkillDictionary) -> Tuple[Optional[Dict], Optional[str]]:
    """(Normalized JD, None) hoac (None, ly do loai)."""
    synthetic = is_synthetic(raw)
    if any(not raw.get(f) for f in REQUIRED_RAW_FIELDS) or (not synthetic and not raw.get("url")):
        return None, REJECT_MISSING
    title, company, description = (_clean(raw.get(k)) for k in ("title", "company", "description_text"))
    if not (title and company and description):
        return None, REJECT_MISSING
    known, unknown = dictionary.resolve(_skill_names(raw))
    title_skills = dictionary.find_in_text(title)
    description_skills = dictionary.find_in_text(description)
    if not is_it_job(title, title_skills, description_skills, known):
        return None, REJECT_NOT_IT
    if len(description) < MIN_DESCRIPTION_CHARS:
        return None, REJECT_MISSING
    skills = sorted(set(known) | set(title_skills) | set(description_skills))
    experience = raw.get("experience_raw") if isinstance(raw.get("experience_raw"), str) else None
    level = normalize_level(title, experience, description, str(raw.get("source") or ""))
    locations = _strings(raw.get("location_raw"))
    salary_min, salary_max, salary_currency = normalize_salary(raw.get("salary_raw"), title)
    sections = {
        "summary": build_summary(title, company, (dictionary.name_of(s) for s in skills), level),
        **split_sections(description),
    }
    return {
        "jd_id": jd_id_of(raw),
        "title": title,
        "company": company,
        "skills": skills,
        "skills_unknown": unknown,
        # Ky nang trong tieu de quyet dinh nhom ("Angular Developer" mo ta nhieu AWS/Nginx van la frontend), hoa thi
        # xet ca JD; tieu de khong co ky nang -> nhom nhieu nhat cua ca JD (Clarifications 2026-10-28)
        "group": dictionary.group_of(title_skills, skills) or dictionary.group_of(skills),
        "level": level,
        "work_type": normalize_work_type(_strings(raw.get("employment_type_raw")), title, *locations),
        "city": normalize_city(locations, description),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": salary_currency,
        "date_posted": raw.get("date_posted") or None,
        "deadline": raw.get("valid_through") or None,
        "sections": sections,
        "language": detect_language(description),
        "content_hash": content_hash(company, title, description),
        "synthetic": synthetic,
        "source_url": raw.get("url") or None,
    }, None
