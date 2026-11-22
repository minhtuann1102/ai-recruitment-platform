"""Van ban embed + ban ghi knowledge_chunks cua JD cho goi y viec lam (spec 017, data-model §1, research R3 / R4).

Van ban: tieu de, "Cap bac", "Nhom", roi doan yeu cau (thieu thi cong viec, thieu nua thi mo ta), cat con 1.200 ky tu.
KHONG co dong ky nang va khong dung sections.summary (da chua dong "Ky nang"): neu embed ky nang thi cosine lap lai
skill_match va phep so sanh tach thanh phan mat y nghia. content_hash = md5 cua chinh van ban da luu (cot CHAR(32)).
"""
import unicodedata
from typing import Dict, Iterable, List, Optional, Tuple

from .qa_record_builder import content_hash

JD_SOURCE_TYPE = "job_description"
JD_MATCH_DATASET = "jd-match"  # metadata.dataset: don / rebuild chi dung vao dataset nay (+ source_type)
JD_MATCH_CHUNK_TYPE = "jd_match_summary"
MAX_TEXT_CHARS = 1200
LANGUAGE_MAX_CHARS = 5  # cot language VARCHAR(5)
BODY_SECTIONS = ("requirements", "responsibilities", "description")  # thu tu uu tien; responsibilities = "Cong viec"


def _body(jd: Dict) -> str:
    sections = jd.get("sections") or {}
    return next((str(sections[key]).strip() for key in BODY_SECTIONS if str(sections.get(key) or "").strip()), "")


def build_match_text(jd: Dict) -> str:
    lines: List[str] = [str(jd.get("title") or "").strip()]
    if jd.get("level"):
        lines.append(f"Cấp bậc: {jd['level']}")
    if jd.get("group"):
        lines.append(f"Nhóm: {jd['group']}")
    body = _body(jd)
    if body:
        lines.append(body)
    text = unicodedata.normalize("NFC", "\n".join(line for line in lines if line))
    return text[:MAX_TEXT_CHARS].rstrip()  # cat roi moi rstrip: noi dung luu = dung chuoi duoc hash


def build_match_record(jd: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """(ban ghi, None) hoac (None, ly do). JD khong co group (khong suy ra track) -> 'no_group'."""
    if not jd.get("group"):
        return None, "no_group"
    text = build_match_text(jd)
    return {
        "content": text,
        "content_hash": content_hash(text),
        "source_type": JD_SOURCE_TYPE,  # bat buoc ghi ro: plan_writes coi thieu khoa la interview_qa
        "category": None,
        "difficulty": None,
        "topic_id": None,
        "language": (jd.get("language") or "")[:LANGUAGE_MAX_CHARS] or None,
        "metadata": {
            "dataset": JD_MATCH_DATASET,
            "chunk_type": JD_MATCH_CHUNK_TYPE,
            "jd_id": jd["jd_id"],
            "title": jd.get("title"),
            "group": jd["group"],
            "level": jd.get("level"),
            "deadline": jd.get("deadline"),
            "skills": list(jd.get("skills") or []),
            "synthetic": bool(jd.get("synthetic")),
        },
    }, None


def build_match_records(jds: Iterable[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """JD -> (ban ghi, bi bo [{jd_id, reason}]). Bo no_group truoc; hai JD trung hash thi giu JD dau (reason
    'duplicate_hash'): moi jd_id toi da mot dong va content_hash la khoa duy nhat cua bang."""
    records: List[Dict] = []
    skipped: List[Dict] = []
    seen = set()
    for jd in jds:
        record, reason = build_match_record(jd)
        if record is not None and record["content_hash"] in seen:
            record, reason = None, "duplicate_hash"
        if record is None:
            skipped.append({"jd_id": jd.get("jd_id"), "reason": reason})
            continue
        seen.add(record["content_hash"])
        records.append(record)
    return records, skipped
