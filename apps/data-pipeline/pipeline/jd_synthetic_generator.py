"""Sinh + hau kiem mot JD synthetic (spec 009 research R9, FR-024, FR-025, FR-027).

Mot JD = mot o (group, level, city) + so thu tu n. Tham so do code chon (jd_synthetic_prompt), LLM viet tieu de + mo ta.
Hau kiem bang code, loi -> goi lai LLM kem ly do (toi da MAX_RETRIES lan) roi bo, khong lap vo han:
JSON dung dang, 0 PII (count_jd_pii), 0 URL, khong cum cam, moi ky nang nhac trong van ban thuoc nhom cua o, va round
trip qua dung build_record cua process-jd: khong bi loai, (group, level, city) suy lai trung o, du section.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import AbstractSet, Callable, Dict, List, Optional, Tuple

from .jd_pii import count_jd_pii
from .jd_record_builder import SYNTHETIC_SOURCE, build_record
from .jd_synthetic_prompt import LOCATION_PREFIX, SynthParams, build_messages, build_params
from .skill_dictionary import SkillDictionary

MAX_RETRIES = 2
REQUIRED_SECTIONS = ("description", "requirements", "benefits")
VALID_DAYS = 30
Completion = Tuple[str, int, int]  # (noi dung, prompt tokens, completion tokens), nhu llm_enricher
CompleteFn = Callable[[List[Dict[str, str]]], Completion]

_URL_RE = re.compile(r"https?://|www\.|(?<![\w@])[\w-]+\.(?:com|vn|io|org|info|dev|app)\b", re.IGNORECASE)
# Bai hoc tu du lieu that (2026-10-28): "Khoa học máy tính" khop bi danh "học máy" (machine-learning); "TS" la bi danh
# TypeScript; "worker node" khop "node" (Node.js). Cum cuoi chi cam ngoai o DevOps.
_BANNED_ALL = (re.compile(r"khoa\s+học\s+máy\s+tính", re.IGNORECASE), re.compile(r"(?<![\w])TS(?![\w])"))
_BANNED_NON_DEVOPS = re.compile(r"worker\s+node", re.IGNORECASE)


@dataclass
class SynthOutcome:
    source_job_id: str
    record: Optional[Dict]  # Raw JD synthetic; None khi bi bo sau retry
    reasons: List[str] = field(default_factory=list)  # ly do loai cua tung lan thu that bai
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


def to_raw_jd(params: SynthParams, title: str, description_text: str, now: datetime) -> Dict:
    """Raw JD dung contract (jd-record-formats.md) + cell / synthetic / source; truong normalizer doc truoc do code dien."""
    group, level, city = params.cell
    return {
        "source": SYNTHETIC_SOURCE,
        "source_job_id": params.source_job_id,
        "url": None,
        "crawled_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "title": title,
        "company": params.company,
        "skills_raw": list(params.skills),
        "description_text": description_text,
        "location_raw": [city],
        "experience_raw": params.experience_raw,
        "employment_type_raw": ["FULL_TIME"],
        "salary_raw": {"currency": "VND", "min": params.salary_min, "max": params.salary_max, "text": None},
        "date_posted": now.date().isoformat(),
        "valid_through": (now.date() + timedelta(days=VALID_DAYS)).isoformat(),
        "synthetic": True,
        "cell": {"group": group, "level": level, "city": city},
    }


def parse_candidate(text: str) -> Optional[Tuple[str, str]]:
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    title, description = data.get("title"), data.get("description_text")
    if not isinstance(title, str) or not isinstance(description, str) or not title.strip() or not description.strip():
        return None
    return " ".join(title.split()), description.strip()


def check_candidate(raw: Dict, params: SynthParams, dictionary: SkillDictionary) -> Optional[str]:
    """None khi JD dat; nguoc lai ly do loai (dua lai cho LLM khi retry)."""
    group, level, city = params.cell
    text = f"{raw['title']}\n{raw['description_text']}"
    if count_jd_pii(text):
        return "pii: co email / so dien thoai / dong lien he / link ho so"
    if _URL_RE.search(text):
        return "url: co URL hoac ten mien"
    if any(p.search(text) for p in _BANNED_ALL) or (group != "devops" and _BANNED_NON_DEVOPS.search(text)):
        return "banned_phrase: co cum bi cam (Khoa hoc may tinh / TS / worker node)"
    if not raw["description_text"].startswith(f"{LOCATION_PREFIX}{city}"):
        return f"location: dong dau phai la '{LOCATION_PREFIX}{city}'"
    foreign = [s for s in dictionary.find_in_text(text) if dictionary.skills[s].group != group]
    if foreign:
        return f"foreign_skill: nhac ky nang ngoai danh sach: {', '.join(dictionary.name_of(s) for s in foreign)}"
    record, reason = build_record(raw, dictionary)
    if record is None:
        return f"process_rejected: {reason}"
    missing = [s for s in REQUIRED_SECTIONS if not record["sections"].get(s)]
    if missing:
        return f"missing_section: {', '.join(missing)}"
    inferred = (record["group"], record["level"], record["city"])
    if inferred != params.cell:
        return f"cell_mismatch: suy lai {inferred}, can {params.cell}"
    return None


def _retry_messages(messages: List[Dict[str, str]], answer: str, reason: str) -> List[Dict[str, str]]:
    feedback = f"Bản trên bị loại vì: {reason}. Viết lại toàn bộ json theo đúng luật."
    return [*messages, {"role": "assistant", "content": answer}, {"role": "user", "content": feedback}]


def generate_one(cell: Tuple[str, str, str], n: int, dictionary: SkillDictionary, complete: CompleteFn,
                 crawl_companies: AbstractSet[str], now: datetime) -> SynthOutcome:
    """Toi da 1 + MAX_RETRIES loi goi LLM cho (o, n); het luot -> record None (dem la loi cua o)."""
    params = build_params(cell, n, dictionary, crawl_companies)
    outcome = SynthOutcome(params.source_job_id, None)
    messages = build_messages(params)
    for _ in range(1 + MAX_RETRIES):
        outcome.calls += 1
        try:
            answer, tokens_in, tokens_out = complete(messages)
        except Exception as exc:  # loi mang / provider (client da tu retry): tinh mot lan thu that bai
            outcome.reasons.append(f"error: {type(exc).__name__}: {str(exc)[:200]}")
            continue
        outcome.tokens_in += tokens_in
        outcome.tokens_out += tokens_out
        parsed = parse_candidate(answer)
        if parsed is None:
            reason = "bad_json: can json object co title va description_text khac rong"
        else:
            raw = to_raw_jd(params, *parsed, now)
            reason = check_candidate(raw, params, dictionary)
            if reason is None:
                outcome.record = raw
                return outcome
        outcome.reasons.append(reason)
        messages = _retry_messages(build_messages(params), answer, reason)
    return outcome
