"""Luat muc tap + bao cao phan bo cho seed Q&A (FR-005, SC-001, SC-002).

Ket qua `valid` la cac cap dua vao xu ly: qua luat muc cap, khong trung qa_id / cau hoi.
Cau hoi trung tuyet doi giu cap co qa_id nho hon de ket qua deterministic.
"""
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List

from .qa_seed_loader import SeedItem
from .qa_seed_rules import Issue, check_pair
from .text_cleaning import clean_text, normalize_for_compare

MIN_PAIRS = 200
MIN_PAIRS_PER_TOPIC = 2
MIN_DIFFICULTY_SHARE = 0.2
MIN_PUBLIC_SHARE = 0.5
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
    kept: List[SeedItem] = []
    seen_ids, seen_questions = set(), {}
    for item in sorted(candidates, key=lambda it: (it.qa_id, it.file, it.index)):
        key = clean_text(item.data["question"]).lower()
        if item.qa_id in seen_ids:
            issues.append(Issue(item.qa_id, "duplicate_qa_id", "error", f"{item.file}#{item.index}: qa_id trung"))
        elif key in seen_questions:
            issues.append(
                Issue(item.qa_id, "duplicate_question", "error", f"cau hoi trung voi {seen_questions[key]}")
            )
        else:
            seen_ids.add(item.qa_id)
            seen_questions[key] = item.qa_id
            kept.append(item)
    return kept


def _warn_near_duplicates(kept: List[SeedItem], issues: List[Issue]) -> None:
    normalized = [(it.qa_id, normalize_for_compare(it.data["question"])) for it in kept]
    for i, (id_a, text_a) in enumerate(normalized):
        for id_b, text_b in normalized[i + 1 :]:
            matcher = SequenceMatcher(None, text_a, text_b)
            if matcher.quick_ratio() >= NEAR_DUPLICATE_RATIO and matcher.ratio() >= NEAR_DUPLICATE_RATIO:
                issues.append(Issue(id_b, "near_duplicate", "warning", f"cau hoi gan trung voi {id_a}"))


def _distribution(kept: List[SeedItem], topics: Dict[str, str], strict: bool, issues: List[Issue]) -> Dict:
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
    for difficulty in ("easy", "medium", "hard"):
        share = by_difficulty[difficulty] / total if total else 0.0
        if share < MIN_DIFFICULTY_SHARE:
            issues.append(Issue(None, "difficulty", level, f"{difficulty} chiem {share:.0%} (can >= 20%)"))
    if public_share < MIN_PUBLIC_SHARE:
        issues.append(Issue(None, "public_share", level, f"cap cong khai chiem {public_share:.0%} (can >= 50%)"))

    return {
        "pairs_valid": total,
        "public_pairs": public,
        "public_share": round(public_share, 4),
        "topics_covered": sum(1 for t in topics if by_topic[t] >= MIN_PAIRS_PER_TOPIC),
        "topics_in_catalog": len(topics),
        "by_category": dict(sorted(Counter(topics[it.data["topic_id"]] for it in kept).items())),
        "by_difficulty": dict(sorted(by_difficulty.items())),
        "by_language": dict(sorted(Counter(it.data["language"] for it in kept).items())),
        "by_license": dict(sorted(Counter(it.data["license"] for it in kept).items())),
        "by_topic": dict(sorted(by_topic.items())),
    }


def validate_seed(items: List[SeedItem], topics: Dict[str, str], strict: bool = False) -> ValidationResult:
    issues: List[Issue] = []
    candidates = []
    for item in items:
        pair_issues = check_pair(item, topics)
        issues.extend(pair_issues)
        if not any(i.level == "error" for i in pair_issues):
            candidates.append(item)
    kept = _drop_duplicates(candidates, issues)
    _warn_near_duplicates(kept, issues)
    report = {"pairs_in": len(items), **_distribution(kept, topics, strict, issues)}
    return ValidationResult(valid=kept, issues=issues, report=report)
