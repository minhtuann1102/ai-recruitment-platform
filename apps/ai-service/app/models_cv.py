"""CvProfile: ket qua CV Parser (docs/ai-service/02 muc 3.3.1). Khong co ten, lien he, ten cong ty."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CvSkill(BaseModel):
    name: str
    category: Literal["language", "framework", "database", "devops", "tool", "concept"]
    evidence: Literal["work", "project", "education", "listed"]


class CvExperience(BaseModel):
    role: str
    company_type: Literal["product", "outsource", "startup", "other", "unknown"] = "unknown"
    start: Optional[str] = None  # YYYY-MM
    end: Optional[str] = None  # null = hien tai
    tech: List[str] = Field(default_factory=list)
    summary: str = ""


class CvProject(BaseModel):
    id: str
    name: str
    role: str = ""
    tech: List[str] = Field(default_factory=list)
    summary: str = ""
    highlights: List[str] = Field(default_factory=list)


class CvEducation(BaseModel):
    degree: str
    year: Optional[int] = None


class CvFlags(BaseModel):
    injection_suspected: bool = False
    truncated: bool = False


class CvProfile(BaseModel):
    schema_version: int = 1
    headline: str
    skills: List[CvSkill] = Field(default_factory=list, max_length=25)
    experiences: List[CvExperience] = Field(default_factory=list, max_length=8)
    projects: List[CvProject] = Field(default_factory=list, max_length=6)
    education: List[CvEducation] = Field(default_factory=list)
    total_years_experience: float = 0.0
    track_relevance: Literal["high", "medium", "low"] = "low"
    flags: CvFlags = Field(default_factory=CvFlags)


class CvParseMetadata(BaseModel):
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class CvParseResponse(BaseModel):
    cv_profile: CvProfile
    metadata: CvParseMetadata
