"""Models cho /api/start, /api/next-turn, /api/finalize (docs/ai-service/06 muc 7.4)."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .models_common import Action, AgentDecision, AnswerType, Level, Phase, TurnKind
from .models_cv import CvProfile
from .models_jd import JdProfile


# --- Plan (Planner, 1 lan dau buoi) ---
class BankQuestion(BaseModel):
    """Cau hoi da kiem chung trong kho interview_qa (RAG); dap an chuan Evaluator lay theo qa_id."""
    qa_id: str
    question: str
    difficulty: Optional[str] = None


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
    bank_questions: List[BankQuestion] = Field(default_factory=list)  # <= 3, chi topic co catalog_ref, RAG bat


class PlanPhase(BaseModel):
    phase: Literal["intro", "technical", "scenario"]
    time_budget_min: int
    topics: List[PlanTopic]


class InterviewPlan(BaseModel):
    schema_version: int = 1
    level_note: Optional[str] = None
    phases: List[PlanPhase]


# --- Candidate state (docs 04 muc 5.2). n_scored / score_sum la truong mock de tinh score_band ---
class TopicState(BaseModel):
    id: str
    status: Literal["pending", "active", "done"] = "pending"
    score_band: Optional[float] = None
    hint_used: bool = False
    turns: List[int] = Field(default_factory=list)
    n_scored: int = 0
    score_sum: float = 0.0
    focus_used: List[str] = Field(default_factory=list)  # focus da hoi (follow-up, hint) de khong hoi lai
    covered: List[str] = Field(default_factory=list)  # y ung vien da neu trong topic (gop qua cac luot, <= 10)


class Counters(BaseModel):
    follow_ups: int = 0
    hints: int = 0
    clarifies: int = 0
    consecutive_dont_know: int = 0


class Tagged(BaseModel):
    tag: str
    turns: List[int] = Field(default_factory=list)


class CandidateState(BaseModel):
    schema_version: int = 1
    phase: Phase = "intro"
    topic_index: int = 1
    active_topic_id: Optional[str] = None
    current_difficulty: int = 2
    difficulty_bounds: dict = Field(default_factory=lambda: {"min": 1, "max": 4})
    momentum: int = 0
    counters: Counters = Field(default_factory=Counters)
    turn_count: int = 0
    evaluated_turns: int = 0
    topics: List[TopicState] = Field(default_factory=list)
    strengths: List[Tagged] = Field(default_factory=list)
    gaps: List[Tagged] = Field(default_factory=list)
    asked_questions: List[str] = Field(default_factory=list)
    end_reason: Optional[str] = None
    # elapsed_seconds luc bat dau phase / topic hien tai (ngan sach thoi gian). None = chua biet (state luu truoc
    # khi co truong nay): luot dau tien gan bang elapsed hien tai thay vi coi topic da chay tu giay 0
    phase_started_s: Optional[int] = None
    topic_started_s: Optional[int] = None
    current_qa_id: Optional[str] = None  # cau vua hoi lay tu kho (dap an chuan cho Evaluator o luot sau)
    used_qa_ids: List[str] = Field(default_factory=list)


class TurnInfo(BaseModel):
    turn_number: int
    phase: Phase
    topic_id: Optional[str]
    turn_kind: TurnKind
    action: Action
    agent_decision: AgentDecision
    difficulty: int
    question_source: Literal["ai", "bank", "fallback"] = "ai"  # bank: tu kho (AI dien dat lai); fallback: cau mau
    qa_id: Optional[str] = None  # cau hoi goc trong kho (question_source = bank)
    reasoning: Optional[str] = None


# --- Requests ---
class StartRequest(BaseModel):
    session_id: str = Field(min_length=1)
    track: str
    level: Level
    duration_minutes: int = Field(default=30, ge=15, le=45)
    cv_profile: Optional[CvProfile] = None
    jd_profile: Optional[JdProfile] = None  # FR-AI-017: khong co thi luyen theo track + level


class TopicTurn(BaseModel):
    q: str
    a: str


class NextTurnRequest(BaseModel):
    session_id: str = Field(min_length=1)
    level: Level
    track: str
    plan: InterviewPlan
    state: CandidateState
    turn_number: int = Field(ge=1)
    question: str
    turn_kind: TurnKind = "main"
    answer: str = Field(min_length=1, max_length=4000)
    topic_turns: List[TopicTurn] = Field(default_factory=list, max_length=5)
    elapsed_seconds: int = Field(default=0, ge=0)


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


# --- Finalize ---
class FinalizeTurn(BaseModel):
    turn_number: int
    phase: Phase
    topic_id: Optional[str] = None
    turn_kind: TurnKind = "main"
    difficulty: int = 2
    question: str
    answer: str
    evaluation: Optional[Evaluation] = None


class FinalizeRequest(BaseModel):
    session_id: str = Field(min_length=1)
    track: str
    level: Level
    plan: InterviewPlan
    state: CandidateState
    end_reason: str
    duration_s: int = Field(ge=0)
    turns: List[FinalizeTurn] = Field(min_length=1)
    jd_profile: Optional[JdProfile] = None  # FR-AI-056: co thi bao cao them khoi requirements
