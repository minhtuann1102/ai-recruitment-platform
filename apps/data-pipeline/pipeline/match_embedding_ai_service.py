"""Nap + goi ma goi y cua ai-service (read-only) cho experiment embedding 017: KHONG chep logic.

apps/ai-service duoc them vao sys.path trong tien trinh experiment. scorer -> settings -> rag.settings -> llm.settings -> app.security
keo theo `fastapi`, ma chi `STRICT_ENVS` duoc dung; venv pipeline khong cai fastapi nen app.security duoc thay bang module gia
chi co hang so do (khong dong logic nao). Moi ham duoi day goi dung ham service.recommend goi: group_for_track, cv_skills,
candidate_level_rank, rank_jobs, va giu gia tri da lam tron cua scorer nhu service._item.
"""
import sys
import types
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence

import numpy as np

AI_SERVICE_DIR = Path(__file__).resolve().parents[2] / "ai-service"
_STRICT_ENVS = frozenset({"staging", "production", "prod"})  # gia tri trong app/security.py (chi hang so nay duoc import)


def load_ai_service() -> SimpleNamespace:
    """Module goi y cua ai-service + MatchSettings mac dinh (trong so 0.6 / 0.3 / 0.1, lech bac toi da 1, toi da 50 ket qua)."""
    if str(AI_SERVICE_DIR) not in sys.path:
        sys.path.insert(0, str(AI_SERVICE_DIR))
    if "app.security" not in sys.modules:
        stub = types.ModuleType("app.security")
        stub.STRICT_ENVS = _STRICT_ENVS
        sys.modules["app.security"] = stub
    from app.matching import cv_text, job_snapshot, levels_tracks, scorer, settings as match_settings
    from app.models_cv import CvProfile
    return SimpleNamespace(cv_text=cv_text, job_snapshot=job_snapshot, levels_tracks=levels_tracks, scorer=scorer,
                           CvProfile=CvProfile, settings=match_settings.load_match_settings({}))


@dataclass
class CvInput:
    cv_id: str
    track: str
    level: str
    text: str  # van ban embed cua CV (cv_text.build_cv_text)
    skills: List[str]  # slug sau chuan hoa
    rank: Optional[int]
    group: Optional[str]


def build_cv_inputs(ai: SimpleNamespace, cvs: Sequence[Dict]) -> List[CvInput]:
    out = []
    for cv in cvs:
        profile = ai.CvProfile.model_validate(cv["cv_profile"])
        slugs, _unknown = ai.cv_text.cv_skills(profile)
        out.append(CvInput(
            cv_id=cv["cv_id"], track=cv["track"], level=cv["level"], text=ai.cv_text.build_cv_text(profile),
            skills=slugs, rank=ai.levels_tracks.candidate_level_rank(cv["level"], profile.total_years_experience),
            group=ai.levels_tracks.group_for_track(cv["track"])))
    return out


def endpoint_items(ai: SimpleNamespace, jobs: Sequence, matrix: np.ndarray, cvs: Sequence[CvInput],
                   cv_vectors: Optional[Dict[str, np.ndarray]], as_of: date, pool_ids: Sequence[str]) -> Dict[str, List[Dict]]:
    """Moi CV: rank_jobs (loc cung + diem 0.6 cosine + 0.3 skill + 0.1 level) -> item dang response cua endpoint.

    matrix: len(jobs) x d, hang da chuan hoa L2 (d tuy model; scorer khong kiem so chieu). Diem va thanh phan la gia tri
    scorer da kep [0, 1] va lam tron 4 chu so, y nhu response that. cv_vectors None = degraded (khong cosine): chi con
    skill_match / level_fit, dung de kiem phan loc cung + skill khi chua co khoa embedding.
    """
    s = ai.settings
    result: Dict[str, List[Dict]] = {}
    for cv in cvs:
        vector = None if cv_vectors is None else cv_vectors[cv.cv_id]
        scored = ai.scorer.rank_jobs(jobs, matrix, vector, cv.skills, group=cv.group, as_of=as_of,
                                     candidate_rank=cv.rank, weights=s.weights, max_level_gap=s.max_level_gap,
                                     max_results=s.max_results, job_ids=pool_ids)
        result[cv.cv_id] = [{"job_id": x.job.job_id, "score": x.score,
                             "components": {"cosine": x.cosine, "skill_match": x.skill_match, "level_fit": x.level_fit}}
                            for x in scored]
    return result


def pool_subset(jobs: Sequence, pool_ids: Sequence[str]):
    """(jobs trong pool theo thu tu chi muc, chi so hang tuong ung) de nhan ma tran vector cua tung model."""
    wanted = set(pool_ids)
    idx = [i for i, job in enumerate(jobs) if job.job_id in wanted]
    return [jobs[i] for i in idx], idx
