"""JdProfile: ket qua JD Parser (FR-AI-016, A11). JD chi vao Planner, khong vao RAG."""
from typing import List, Literal

from pydantic import BaseModel, Field

from .models_cv import CvParseMetadata


class JdRequirement(BaseModel):
    id: str  # r1, r2... de bao cao khoi `requirements` tham chieu (FR-AI-056)
    text: str = Field(max_length=150)
    kind: Literal["must", "nice"]
    topic_ids: List[str] = Field(default_factory=list, max_length=3)  # topic trong catalog cua track
    out_of_catalog: bool = False  # khong map duoc ve catalog: bao cao ghi out_of_catalog, khong ep


class JdFlags(BaseModel):
    injection_suspected: bool = False
    truncated: bool = False


class JdProfile(BaseModel):
    schema_version: int = 1
    title: str = Field(default="", max_length=120)
    requirements: List[JdRequirement] = Field(default_factory=list, max_length=15)
    flags: JdFlags = Field(default_factory=JdFlags)

    def priority_topic_ids(self) -> List[str]:
        """Topic theo thu tu uu tien cho Planner (FR-AI-023): must truoc, nice sau, khong trung."""
        ordered: List[str] = []
        for kind in ("must", "nice"):
            for r in self.requirements:
                if r.kind == kind:
                    ordered += [t for t in r.topic_ids if t not in ordered]
        return ordered


class JdParseRequest(BaseModel):
    track: str
    jd_text: str = Field(min_length=50, max_length=20000)


class JdParseResponse(BaseModel):
    jd_profile: JdProfile
    metadata: CvParseMetadata
