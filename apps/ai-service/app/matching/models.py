"""Request / response cua POST /api/match/jobs (contracts/match-jobs-api.md, snake_case).

track la str tu do: track la phai ra 422 unknown_track (router), khong phai invalid_request cua handler chung.
Level sai thi handler chung tra 422 invalid_request.
"""
import re
from datetime import date, datetime
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator

from ..models_common import Level
from ..models_cv import CvProfile
from .settings import MatchWeights

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
DegradedReason = Literal["embedding_unavailable", "embedding_timeout", "embedding_error"]


class MatchJobsRequest(BaseModel):
    cv_profile: CvProfile
    track: str
    level: Optional[Level] = None  # khong co thi suy tu so nam kinh nghiem
    as_of: Optional[date] = None  # mac dinh ngay hien tai (Asia/Ho_Chi_Minh), service dien
    job_ids: Optional[List[Annotated[str, StringConstraints(min_length=1)]]] = Field(
        default=None, min_length=1, max_length=200)  # chi xet cac JD nay (danh gia, GD2)
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=50)

    @field_validator("as_of", mode="before")
    @classmethod
    def _only_yyyy_mm_dd(cls, value):
        # pydantic mac dinh nhan ca so nguyen (epoch) va chuoi co gio; contract chi nhan YYYY-MM-DD
        if value is None or isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, str) and _ISO_DATE.fullmatch(value):
            return value
        raise ValueError("as_of phai co dang YYYY-MM-DD")


class MatchComponents(BaseModel):
    cosine: Optional[float] = None  # null khi degraded (khong co vector CV)
    skill_match: float
    level_fit: float


class MatchItem(BaseModel):
    job_id: str
    title: str
    group: str
    level: Optional[str] = None  # nhan goc cua JD (Intern|Junior|Mid|Senior|Lead|Manager)
    deadline: Optional[date] = None
    score: float
    components: MatchComponents
    matched_skills: List[str] = Field(default_factory=list)  # ten hien thi
    missing_skills: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)  # jd_no_skills | jd_no_level


class MatchUsage(BaseModel):
    embedding_tokens: int = 0


class MatchTiming(BaseModel):
    embed: int = 0
    score: int = 0
    total: int = 0


class MatchMetadata(BaseModel):
    as_of: date
    weights: MatchWeights  # trong so thuc dung (da chuan hoa lai khi degraded)
    max_level_gap: int
    candidate_level_rank: Optional[int] = None
    embedding_model: str
    index_size: int
    index_loaded_at: Optional[datetime] = None
    cv_skill_count: int
    unknown_skills_count: int
    degraded: bool = False
    degraded_reason: Optional[DegradedReason] = None
    mock: bool = False
    usage: MatchUsage = Field(default_factory=MatchUsage)
    timing_ms: MatchTiming = Field(default_factory=MatchTiming)


class MatchJobsResponse(BaseModel):
    items: List[MatchItem]
    page: int
    page_size: int
    total: int  # min(so JD qua loc cung, MATCH_MAX_RESULTS)
    metadata: MatchMetadata
