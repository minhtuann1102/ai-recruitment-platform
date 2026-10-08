"""Schema topic catalog: moi track (vi tri phong van) la mot file YAML trong thu muc nay.

Planner chi duoc chon topic co trong catalog (xem docs/ai-service/02-multi-agent-architecture-and-prompts.md).
Truong `resources` (link tai lieu hoc) do DE bo sung sau, chua co o day.
"""
from typing import List, Literal

from pydantic import BaseModel, Field, model_validator

Level = Literal["fresher", "junior", "middle", "senior"]
# Khop cot knowledge_chunks.category (xem docs/architecture/rag-design.md)
Category = Literal["Backend", "Database", "System Design", "DevOps", "AI"]


class Topic(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
    title: str = Field(min_length=3)
    levels: List[Level] = Field(min_length=1)
    category: Category
    key_concepts: List[str] = Field(min_length=3, max_length=8)


class Scenario(BaseModel):
    id: str = Field(pattern=r"^scn\.[a-z0-9]+\.[a-z0-9-]+$")
    title: str = Field(min_length=5)
    levels: List[Level] = Field(min_length=1)


class TrackCatalog(BaseModel):
    track: str = Field(pattern=r"^[a-z]+(_[a-z]+)*$")
    title: str
    id_prefix: str  # moi topic.id phai bat dau bang "<id_prefix>."
    topics: List[Topic]
    scenarios: List[Scenario]

    @model_validator(mode="after")
    def _check_ids(self):
        ids = [t.id for t in self.topics] + [s.id for s in self.scenarios]
        if len(set(ids)) != len(ids):
            raise ValueError(f"track {self.track}: id bi trung")
        for t in self.topics:
            if not t.id.startswith(self.id_prefix + "."):
                raise ValueError(f"topic {t.id} khong bat dau bang '{self.id_prefix}.'")
        return self

    def topics_for(self, level: Level) -> List[Topic]:
        return [t for t in self.topics if level in t.levels]

    def scenarios_for(self, level: Level) -> List[Scenario]:
        return [s for s in self.scenarios if level in s.levels]
