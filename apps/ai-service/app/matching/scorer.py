"""Loc cung va tinh diem goi y viec lam: ham thuan, chi numpy, khong DB / mang (spec 017 FR-007..FR-010, FR-013,
FR-014; data-model muc 4).

score = w1 * cosine + w2 * skill_match + w3 * level_fit. Khi degraded (khong co vector CV): bo cosine, w2 / w3 chuan
hoa lai cho cong bang 1. Diem va thanh phan lam tron ROUND_DIGITS chu so ngay trong scorer, sap xep tren gia tri da
lam tron: thu tu hien thi dung la thu tu sap (hoa -> job_id) va khong phu thuoc nhieu so thuc giua cac may.
"""
from dataclasses import dataclass
from datetime import date
from typing import Collection, FrozenSet, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .settings import MatchWeights
from .skill_normalizer import display_name

ROUND_DIGITS = 4


@dataclass(frozen=True)
class IndexedJob:
    """Mot JD trong snapshot chi muc (data-model muc 2). level la nhan goc cua JD de tra ve ("Mid")."""
    job_id: str
    title: str
    group: str
    level: Optional[str]
    level_rank: Optional[int]
    deadline: Optional[date]
    skills: FrozenSet[str]  # slug


@dataclass(frozen=True)
class ScoredJob:
    job: IndexedJob
    score: float
    cosine: Optional[float]  # None khi degraded
    skill_match: float
    level_fit: float
    matched_skills: Tuple[str, ...]  # ten hien thi, theo thu tu slug
    missing_skills: Tuple[str, ...]
    notes: Tuple[str, ...]  # jd_no_skills | jd_no_level


def l2_normalize(vector: np.ndarray) -> np.ndarray:
    """Chuan hoa L2; vector 0 giu nguyen (khong NaN)."""
    vector = np.asarray(vector, dtype=np.float64)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


def cosine_scores(cv_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """max(0, cos) cho moi hang cua matrix (hang da chuan hoa L2), kep [0, 1] (FR-008)."""
    return np.clip(np.asarray(matrix, dtype=np.float64) @ l2_normalize(cv_vector), 0.0, 1.0)


def skill_overlap(jd_skills: Collection[str], cv_skills: Collection[str]) -> Tuple[float, List[str], List[str]]:
    """(|JD giao CV| / |JD|, slug khop, slug thieu), hai danh sach theo thu tu slug. JD rong -> 0."""
    if not jd_skills:
        return 0.0, [], []
    matched = sorted(set(jd_skills) & set(cv_skills))
    missing = sorted(set(jd_skills) - set(cv_skills))
    return len(matched) / len(jd_skills), matched, missing


def level_fit(jd_rank: Optional[int], candidate_rank: Optional[int]) -> float:
    """1 cung bac, 0.5 lech 1 bac hoac thieu level o mot trong hai ben, 0 lech hon."""
    if jd_rank is None or candidate_rank is None:
        return 0.5
    gap = abs(jd_rank - candidate_rank)
    return 1.0 if gap == 0 else 0.5 if gap == 1 else 0.0


def effective_weights(weights: MatchWeights, degraded: bool) -> MatchWeights:
    """Trong so thuc dung. degraded: cosine = 0, w2 / w3 chia lai theo ty le (neu w2 + w3 = 0 thi moi diem la 0)."""
    if not degraded:
        return weights
    rest = weights.skill_match + weights.level_fit
    if rest <= 0:
        return MatchWeights(0.0, 0.0, 0.0)
    return MatchWeights(0.0, weights.skill_match / rest, weights.level_fit / rest)


def passes_hard_filter(job: IndexedJob, *, group: str, as_of: date, candidate_rank: Optional[int],
                       max_level_gap: int) -> bool:
    """Cung nhom, han nop >= as_of, lech bac <= max_level_gap. JD khong co han hoac khong co level, hay ung vien
    khong co bac, thi khong bi loc theo tieu chi do."""
    if job.group != group:
        return False
    if job.deadline is not None and job.deadline < as_of:
        return False
    if job.level_rank is not None and candidate_rank is not None:
        return abs(job.level_rank - candidate_rank) <= max_level_gap
    return True


def _round(value: float) -> float:
    return round(float(value), ROUND_DIGITS)


def rank_jobs(jobs: Sequence[IndexedJob], matrix: np.ndarray, cv_vector: Optional[np.ndarray],
              cv_skills: Collection[str], *, group: str, as_of: date, candidate_rank: Optional[int],
              weights: MatchWeights, max_level_gap: int, max_results: int,
              job_ids: Optional[Iterable[str]] = None) -> List[ScoredJob]:
    """Loc cung (kem gioi han job_ids), cham diem, sap diem giam dan / hoa thi job_id tang dan, cat max_results.
    matrix: N x dims, hang i ung voi jobs[i], da chuan hoa L2. cv_vector None = degraded (bo qua matrix)."""
    allowed = None if job_ids is None else set(job_ids)
    picked = [i for i, job in enumerate(jobs)
              if (allowed is None or job.job_id in allowed)
              and passes_hard_filter(job, group=group, as_of=as_of, candidate_rank=candidate_rank,
                                     max_level_gap=max_level_gap)]
    degraded = cv_vector is None
    w = effective_weights(weights, degraded)
    cosines = None if degraded or not picked else cosine_scores(cv_vector, np.asarray(matrix)[picked])

    scored = [_score_job(jobs[i], None if cosines is None else float(cosines[n]), cv_skills, candidate_rank, w)
              for n, i in enumerate(picked)]
    scored.sort(key=lambda s: (-s.score, s.job.job_id))
    return scored[:max_results]


def _score_job(job: IndexedJob, cosine: Optional[float], cv_skills: Collection[str],
               candidate_rank: Optional[int], w: MatchWeights) -> ScoredJob:
    skill_value, matched, missing = skill_overlap(job.skills, cv_skills)
    fit = level_fit(job.level_rank, candidate_rank)
    raw = w.skill_match * skill_value + w.level_fit * fit + (w.cosine * cosine if cosine is not None else 0.0)
    notes = []
    if not job.skills:
        notes.append("jd_no_skills")
    if job.level_rank is None:
        notes.append("jd_no_level")
    return ScoredJob(
        job=job, score=_round(raw), cosine=None if cosine is None else _round(cosine),
        skill_match=_round(skill_value), level_fit=fit, matched_skills=tuple(display_name(s) for s in matched),
        missing_skills=tuple(display_name(s) for s in missing), notes=tuple(notes))
