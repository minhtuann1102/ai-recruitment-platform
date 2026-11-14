"""Models cua ket qua cham (Evaluation) va tai lieu doi chieu (SourceRef): tach khoi models_interview cho file gon.

models_interview re-export cac ten nay nen `from app.models_interview import Evaluation` van dung.
"""
import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .models_common import AnswerType

_HTTP_URL = re.compile(r"https?://\S+")


class SourceRef(BaseModel):
    """Tai lieu doi chieu ben vung qua luot (Phase 03b): ref = qa_id / id chunk, title = dong dau (cau hoi), url DE."""
    ref: str
    title: str
    url: Optional[str] = None
    license: Optional[str] = None  # giay phep cua chunk / cau tu kho (metadata DE, chi de tra cuu); None = chua biet

    @field_validator("url")
    @classmethod
    def _http_only(cls, url: Optional[str]) -> Optional[str]:
        # plan / evaluation do interview-service gui lai: kiem ca luc vao lai, khong chi luc tao tu chunk
        return url if url and _HTTP_URL.fullmatch(url) else None

    @field_validator("title")
    @classmethod
    def _short_title(cls, title: str) -> str:
        return title[:150]


# --- Evaluation ---
class Bands(BaseModel):
    technical_accuracy: int = Field(ge=0, le=4)
    completeness: int = Field(ge=0, le=4)
    extensibility: int = Field(ge=0, le=4)
    relevance: int = Field(ge=0, le=4)


class Scores10(BaseModel):
    technical_accuracy: float
    completeness: float
    extensibility: float
    relevance: float


Support = Literal["supported", "contradicted", "no_source"]


class CitedSource(SourceRef):
    """Tai lieu Evaluator v4 trich trong luot: id theo vi tri (S1.., R) + muc ung ho cua y trich no."""
    id: str
    support: Support


class Evidence(BaseModel):
    claim: str
    quote: str
    # Evaluator v4 (Phase 03a): id tai lieu doi chieu trong luot (S1.. snippet, R dap an chuan); None = v3 / mock
    source_ids: List[str] = Field(default_factory=list)
    support: Optional[Support] = None


class Evaluation(BaseModel):
    turn_number: int
    answer_type: AnswerType
    covered_points: List[str] = Field(default_factory=list)
    missing_points: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    scores: Bands
    scores_10: Scores10
    turn_score_10: float
    degraded: bool = False
    strength_tags: List[str] = Field(default_factory=list)
    gap_tags: List[str] = Field(default_factory=list)
    follow_up_focus: Optional[str] = None
    # v4: low = luot co tai lieu nhung khong y covered nao duoc tai lieu ung ho (diem khong bam nguon); None = v3 / mock
    confidence: Optional[Literal["high", "low"]] = None
    sources: List[CitedSource] = Field(default_factory=list)  # 03b: Reporter lay tai lieu cho study_plan tu day
    prompt_version: Optional[str] = None  # ban prompt da cham; None = khong qua LLM (mock, luat code, degraded)
    reference_missing: bool = False  # cau trong kho nhung khong lay duoc dap an chuan luc cham (ai_db loi / qua han)
    transcript_low_confidence: bool = False  # ban ghi STT duoi nguong tin cay: khong cham, khong tinh diem
