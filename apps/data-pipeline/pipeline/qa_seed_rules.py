"""Luat kiem tra muc cap Q&A (contracts/qa-seed-format.md), dung chung cho validate va process.

validate: loi bat ky -> thoat 1. process/index: cap co loi bi loai kem ly do, chay tiep (US2-1).
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .pii_patterns import find_pii
from .qa_seed_loader import SeedItem
from .text_cleaning import clean_text

# Giay phep cho phep sua doi + phan phoi lai (FR-003, research R6). Ngoai danh sach (ND/NC, GPL,
# khong ro) la loi.
LICENSE_ALLOWLIST = frozenset({"CC0-1.0", "MIT", "Apache-2.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-SA-2.5"})
# Giay phep cua ca bo seed, khai trong data/seeds/interview_qa/NOTICE; cap tu soan dung giay phep nay.
# Them nguon CC-BY-SA thi phai doi ca bo sang CC-BY-SA-4.0 (share-alike).
DATASET_LICENSE = "CC-BY-4.0"
SELF_SOURCE = "self"
DIFFICULTIES = ("easy", "medium", "hard")
LANGUAGES = ("vi", "en")
REQUIRED_FIELDS = {
    "qa_id": str,
    "topic_id": str,
    "question": str,
    "answer": str,
    "difficulty": str,
    "language": str,
    "source": str,
    "license": str,
    "synthetic": bool,
}
QA_ID_RE = re.compile(r"^de-qa-\d{4}$")
URL_RE = re.compile(r"^https?://\S+$")
MIN_QUESTION_CHARS = 10
MIN_ANSWER_CHARS = 30


@dataclass(frozen=True)
class Issue:
    qa_id: Optional[str]  # None voi luat muc tap (phan bo)
    rule: str
    level: str  # error | warning
    message: str


def _non_empty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_pair(item: SeedItem, topics: Dict[str, str]) -> List[Issue]:
    qa_id = item.qa_id
    issues: List[Issue] = []

    def error(rule: str, message: str) -> None:
        issues.append(Issue(qa_id, rule, "error", f"{item.file}#{item.index}: {message}"))

    pair = item.data
    if not isinstance(pair, dict):
        error("schema", "phan tu khong phai object")
        return issues
    for field, kind in REQUIRED_FIELDS.items():
        if not isinstance(pair.get(field), kind):
            error("schema", f"thieu hoac sai kieu truong '{field}' (can {kind.__name__})")
    if issues:
        return issues

    if not QA_ID_RE.match(pair["qa_id"]):
        error("qa_id", f"qa_id '{pair['qa_id']}' khong khop de-qa-NNNN")
    if pair["topic_id"] not in topics:
        error("topic_id", f"topic_id '{pair['topic_id']}' khong phai topic trong catalog (scenario khong hop le)")
    if len(clean_text(pair["question"])) < MIN_QUESTION_CHARS:
        error("length", f"question < {MIN_QUESTION_CHARS} ky tu sau lam sach")
    if len(clean_text(pair["answer"])) < MIN_ANSWER_CHARS:
        error("length", f"answer < {MIN_ANSWER_CHARS} ky tu sau lam sach")
    if pair["difficulty"] not in DIFFICULTIES:
        error("enum", f"difficulty '{pair['difficulty']}' khong thuoc {DIFFICULTIES}")
    if pair["language"] not in LANGUAGES:
        error("enum", f"language '{pair['language']}' khong thuoc {LANGUAGES}")
    tags = pair.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(t, str) or t != t.lower() for t in tags) or len(set(tags)) != len(tags):
        error("tags", "tags phai la mang string chu thuong, khong trung")

    if pair["license"] not in LICENSE_ALLOWLIST:
        error("license", f"giay phep '{pair['license']}' khong thuoc danh sach cho phep")
    elif pair["license"].startswith("CC-BY-SA") and not DATASET_LICENSE.startswith("CC-BY-SA"):
        error("license", f"nguon share-alike: doi giay phep bo seed sang CC-BY-SA-4.0 (NOTICE, DATASET_LICENSE)")
    if pair["source"] == SELF_SOURCE and pair["license"] != DATASET_LICENSE:
        error("license", f"cap tu soan phai dung giay phep bo seed {DATASET_LICENSE}")
    if pair["source"] != SELF_SOURCE:
        if not URL_RE.match(pair["source"]):
            error("provenance", "source phai la URL hoac 'self'")
        if not _non_empty_str(pair.get("attribution")):
            error("provenance", "cap co noi dung tu nguon ngoai phai co attribution")
    elif not pair["synthetic"]:
        error("provenance", "synthetic=false nhung source='self' (cap cong khai can URL nguon)")
    # Moi cap deu qua nguoi doc: cap cong khai cung la ban dich/chuyen the, phai doi chieu ban goc
    if not _non_empty_str(pair.get("reviewed_by")):
        error("review", "thieu reviewed_by: chi dien sau khi nguoi review da doc (va doi chieu ban goc neu dich)")

    for field in ("question", "answer"):
        for kind, value in find_pii(pair[field]):
            error("pii", f"{field} chua {kind}: {value}")
    return issues
