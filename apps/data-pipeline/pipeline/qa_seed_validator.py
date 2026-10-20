"""Luat muc tap + bao cao phan bo cho seed Q&A (FR-005, SC-001, SC-002).

Ket qua `valid` la cac cap dua vao xu ly: qua luat muc cap, khong trung qa_id / cau hoi.
Cau hoi trung tuyet doi: uu tien seed curated, roi qa_id nho hon (deterministic).
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from .qa_seed_loader import SeedItem
from .qa_seed_rules import SELF_SOURCE, Issue, check_pair
from .settings import CURATED_DATASET
from .text_cleaning import clean_text, normalize_for_compare

MIN_PAIRS = 200
MIN_PAIRS_PER_TOPIC = 2
# SC-001 (sua 2026-10-19): topic co level middle/senior can >= 2 cap hard
MIN_HARD_PER_TOPIC = 2
NEAR_DUPLICATE_RATIO = 0.9


@dataclass
class ValidationResult:
    valid: List[SeedItem]
    issues: List[Issue] = field(default_factory=list)
    report: Dict = field(default_factory=dict)

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def rejected_qa_ids(self) -> List[str]:
        return sorted({i.qa_id for i in self.errors if i.qa_id is not None})


def _drop_duplicates(candidates: List[SeedItem], issues: List[Issue]) -> List[SeedItem]:
    """Bo cap trung qa_id / cau hoi. Seed curated xep truoc nen luon duoc giu khi trung voi cap crawl.

    Trung giua hai cap curated la loi (nguoi soan phai sua); cap crawl trung (cac nguon chong lan,
    dich ra cung cau) chi canh bao va bi bo, output van 0 cap trung (SC-002).
    """
    kept: List[SeedItem] = []
    seen_ids, seen_questions = set(), {}
    order = sorted(candidates, key=lambda it: (it.dataset != CURATED_DATASET, it.qa_id, it.file, it.index))
    for item in order:
        key = clean_text(item.data["question"]).lower()
        level = "error" if item.dataset == CURATED_DATASET else "warning"
        if item.qa_id in seen_ids:
            issues.append(Issue(item.qa_id, "duplicate_qa_id", level, f"{item.file}#{item.index}: qa_id trung"))
        elif key in seen_questions:
            issues.append(Issue(item.qa_id, "duplicate_question", level, f"cau hoi trung voi {seen_questions[key]}"))
        else:
            seen_ids.add(item.qa_id)
            seen_questions[key] = item.qa_id
            kept.append(item)
    return sorted(kept, key=lambda it: (it.qa_id, it.file, it.index))


def _warn_near_duplicates(kept: List[SeedItem], issues: List[Issue]) -> None:
    """So cap trong cung topic_id (O(n^2) toan bo mat ~3.5 phut voi ~4.800 cap)."""
    by_topic: Dict[str, List] = defaultdict(list)
    for it in kept:
        by_topic[it.data["topic_id"]].append((it.qa_id, normalize_for_compare(it.data["question"])))
    for normalized in by_topic.values():
        for i, (id_a, text_a) in enumerate(normalized):
            for id_b, text_b in normalized[i + 1 :]:
                matcher = SequenceMatcher(None, text_a, text_b)
                if matcher.quick_ratio() >= NEAR_DUPLICATE_RATIO and matcher.ratio() >= NEAR_DUPLICATE_RATIO:
                    issues.append(Issue(id_b, "near_duplicate", "warning", f"cau hoi gan trung voi {id_a}"))


def source_key(source: str) -> str:
    """Gom nguon de bao cao: 'self', 'owner/repo' voi GitHub, hoac ten mien."""
    if source == SELF_SOURCE:
        return SELF_SOURCE
    parsed = urlparse(source)
    parts = [p for p in parsed.path.split("/") if p]
    if parsed.netloc.endswith("github.com") and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parsed.netloc or source


def _distribution(
    kept: List[SeedItem], pending: List[SeedItem], topics: Dict[str, str], hard_topics: Set[str], strict: bool, issues: List[Issue]
) -> Dict:
    """Phan bo tren cap da vao kho (kept); `pending` = cap seed chi thieu reviewed_by, dem rieng de thay sau khi duyet."""
    level = "error" if strict else "warning"
    total = len(kept)
    by_topic = Counter(it.data["topic_id"] for it in kept)
    by_difficulty = Counter(it.data["difficulty"] for it in kept)
    public = sum(1 for it in kept if not it.data["synthetic"])
    public_share = public / total if total else 0.0

    thin_topics = sorted(t for t in topics if by_topic[t] < MIN_PAIRS_PER_TOPIC)
    if thin_topics:
        issues.append(Issue(None, "coverage", level, f"{len(thin_topics)} topic co < {MIN_PAIRS_PER_TOPIC} cap: {', '.join(thin_topics)}"))
    if total < MIN_PAIRS:
        issues.append(Issue(None, "total", level, f"chi co {total} cap hop le (can >= {MIN_PAIRS})"))
    hard_by_topic = Counter(it.data["topic_id"] for it in kept if it.data["difficulty"] == "hard")
    missing_hard = sorted(t for t in hard_topics if hard_by_topic[t] < MIN_HARD_PER_TOPIC)
    hard_by_topic_after_review = hard_by_topic + Counter(it.data["topic_id"] for it in pending if it.data["difficulty"] == "hard")
    missing_hard_after_review = [t for t in hard_topics if hard_by_topic_after_review[t] < MIN_HARD_PER_TOPIC]
    if missing_hard:
        issues.append(Issue(None, "hard_coverage", level, f"{len(missing_hard)} topic middle/senior co < {MIN_HARD_PER_TOPIC} cap hard: {', '.join(missing_hard)}"))

    return {
        "pairs_valid": total,
        "public_pairs": public,
        "public_share": round(public_share, 4),
        "topics_covered": sum(1 for t in topics if by_topic[t] >= MIN_PAIRS_PER_TOPIC),
        "topics_in_catalog": len(topics),
        "topics_missing_hard": len(missing_hard),
        "topics_missing_hard_after_review": len(missing_hard_after_review),
        "pairs_pending_review": len(pending),
        "by_dataset": dict(sorted(Counter(it.dataset for it in kept).items())),
        "by_category": dict(sorted(Counter(topics[it.data["topic_id"]] for it in kept).items())),
        "by_difficulty": dict(sorted(by_difficulty.items())),
        "by_language": dict(sorted(Counter(it.data["language"] for it in kept).items())),
        "by_license": dict(sorted(Counter(it.data["license"] for it in kept).items())),
        "by_source": dict(sorted(Counter(source_key(it.data["source"]) for it in kept).items())),
        "by_topic": dict(sorted(by_topic.items())),
    }


def validate_seed(
    items: List[SeedItem],
    topics: Dict[str, str],
    strict: bool = False,
    near_duplicates: bool = True,
    hard_topics: Optional[Set[str]] = None,
) -> ValidationResult:
    """near_duplicates=False cho process/index: buoc nay chi sinh canh bao, khong doi ket qua.
    hard_topics: topic can >= 2 cap hard (level middle/senior); None = khong kiem.
    """
    issues: List[Issue] = []
    candidates, pending = [], []
    for item in items:
        pair_issues = check_pair(item, topics)
        if pair_issues and item.dataset != CURATED_DATASET:
            # Du lieu crawl hang nghin cap: cap loi bi loai va bao canh bao, khong chan ca bo (nhu cap trung)
            pair_issues = [Issue(i.qa_id, i.rule, "warning", i.message) for i in pair_issues]
            issues.extend(pair_issues)
            continue
        issues.extend(pair_issues)
        error_rules = {i.rule for i in pair_issues if i.level == "error"}
        if not error_rules:
            candidates.append(item)
        elif error_rules == {"review"}:
            # Chi thieu reviewed_by: van kiem trung / gan trung ngay, nhung chua vao kho cho toi khi duyet
            pending.append(item)
    pending_ids = {it.qa_id for it in pending}
    checked = _drop_duplicates(candidates + pending, issues)
    kept = [it for it in checked if it.qa_id not in pending_ids]
    if near_duplicates:
        _warn_near_duplicates(checked, issues)
    still_pending = [it for it in checked if it.qa_id in pending_ids]
    report = {"pairs_in": len(items), **_distribution(kept, still_pending, topics, hard_topics or set(), strict, issues)}
    return ValidationResult(valid=kept, issues=issues, report=report)
