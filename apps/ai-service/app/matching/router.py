"""POST /api/match/jobs (contracts/match-jobs-api.md): endpoint noi bo, X-Internal-Token do middleware kiem.

Loi: 401 (middleware), 422 invalid_request (handler chung trong main.py), 422 unknown_track va 503
match_index_unavailable (ApiError tu service / job_index).
"""
from fastapi import APIRouter

from .models import MatchJobsRequest, MatchJobsResponse
from .service import get_match_service

router = APIRouter()


@router.post("/api/match/jobs", response_model=MatchJobsResponse)
async def match_jobs(req: MatchJobsRequest) -> MatchJobsResponse:
    """Goi y JD phu hop voi CV: loc cung (track, han nop, lech level), diem = cosine + skill_match + level_fit."""
    return await get_match_service().recommend(req)
