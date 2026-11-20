"""Models cua plan phong van (Planner, 1 lan dau buoi); models_interview re-export de import cu van chay."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .models_evaluation import SourceRef


class BankQuestion(BaseModel):
    """Cau hoi da kiem chung trong kho interview_qa (RAG); dap an chuan Evaluator lay theo qa_id."""
    qa_id: str
    question: str
    difficulty: Optional[str] = None
    license: Optional[str] = None  # giay phep cua cap Q&A (DE), chuyen sang SourceRef; khong dung de loc


class PlanTopic(BaseModel):
    id: str
    title: str
    source: Literal["cv", "catalog", "scenario", "generic"]
    cv_ref: Optional[str] = None
    catalog_ref: Optional[str] = None
    objective: str
    key_points: List[str] = Field(min_length=3, max_length=6)
    start_difficulty: int = Field(ge=1, le=5)
    opening_hint: str
    backup_question: str
    reference_snippets: List[str] = Field(default_factory=list)
    reference_sources: List[SourceRef] = Field(default_factory=list)  # cung thu tu reference_snippets (03b)
    bank_questions: List[BankQuestion] = Field(default_factory=list)  # <= 3, chi topic co catalog_ref, RAG bat


class PlanPhase(BaseModel):
    phase: Literal["intro", "technical", "scenario"]
    time_budget_min: int
    topics: List[PlanTopic]


class ReplanPool(BaseModel):
    """Phase 05: topic du phong `alt{n}` (ngoai phases) + id topic plan khong duoc bo (map tu yeu cau JD)."""
    reserve: List[PlanTopic] = Field(default_factory=list, max_length=2)
    keep_ids: List[str] = Field(default_factory=list)


class InterviewPlan(BaseModel):
    schema_version: int = 1
    level_note: Optional[str] = None
    phases: List[PlanPhase]
    replan: Optional[ReplanPool] = None  # None: khong lap lai ke hoach (co tat, plan cu, hoac khong con topic du phong)
