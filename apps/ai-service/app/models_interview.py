"""Models cho /api/start, /api/next-turn, /api/finalize (docs/ai-service/06 muc 7.4)."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .models_common import Action, AgentDecision, Level, Phase, TurnKind
from .models_cv import CvProfile
from .models_evaluation import (Bands, CitedSource, Evaluation, Evidence, Scores10, SourceRef,  # noqa: F401  (re-export)
                                Support)
from .models_jd import JdProfile

# --- Plan (Planner, 1 lan dau buoi) ---
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
    """Phase 05 (REPLAN_ENABLED): topic du phong id `alt{n}` (khong nam trong phases) va id topic plan khong duoc bo
    (map tu yeu cau JD). Chi co khi start chay voi co bat va co it nhat 1 topic du phong."""
    reserve: List[PlanTopic] = Field(default_factory=list, max_length=2)
    keep_ids: List[str] = Field(default_factory=list)


class InterviewPlan(BaseModel):
    schema_version: int = 1
    level_note: Optional[str] = None
    phases: List[PlanPhase]
    replan: Optional[ReplanPool] = None  # None: khong lap lai ke hoach (co tat, plan cu, hoac khong con topic du phong)


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
    stt_reasks: int = 0  # NFR-AI-QUAL17: so lan hoi lai vi ban ghi giong noi kem trong topic (toi da 1)


class Tagged(BaseModel):
    tag: str
    turns: List[int] = Field(default_factory=list)


class Swap(BaseModel):
    """Mot lan doi topic technical `pending` (drop) lay topic du phong (add) tai cung vi tri (phase 05)."""
    drop: str
    add: str
    turn: int
    reason: str = ""  # qua safe_focus + loc PII, <= 20 tu


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
    swaps: List[Swap] = Field(default_factory=list)  # phase 05: cac lan doi topic; state cu khong co thi rong


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
    # phase 04, chi gan khi POLICY_MODE=hybrid (rules: None). proposed / policy la hanh dong TRUOC apply_action
    # (next_topic chua doi thanh ask_main) va truoc low_performance_stop; action la sau apply.
    decided_by: Optional[Literal["llm", "policy", "forced"]] = None
    proposed_action: Optional[str] = None   # hanh dong Evaluator v9 de xuat (None: khong co de xuat)
    policy_action: Optional[str] = None     # hanh dong luat decide() se chon (phan thuc cua LLM)
    overrule_reason: Optional[str] = None   # vi sao bac de xuat; None khi dung de xuat hoac forced
    action_reason: Optional[str] = None     # ly do cua LLM da qua kiem (injection / PII thi None)
    # phase 05, chi gan khi LLM de xuat doi topic (REPLAN_ENABLED): applied | budget | bad_drop | jd_priority | bad_add
    # | not_applicable. Doi that thi turn nay hoi topic `alt*` (xem state.swaps), plan tra ve client khong doi.
    swap_result: Optional[str] = None


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
    source: Optional[Literal["text", "voice"]] = None  # None: cung nguon voi luot hien tai (answer_source)


class NextTurnRequest(BaseModel):
    session_id: str = Field(min_length=1)
    level: Level
    track: str
    plan: InterviewPlan
    state: CandidateState
    turn_number: int = Field(ge=1)
    question: str
    turn_kind: TurnKind = "main"
    answer: str = Field(max_length=4000)  # voice duoc rong (micro khong thu tieng): turn_engine tra voice_no_speech
    topic_turns: List[TopicTurn] = Field(default_factory=list, max_length=5)
    elapsed_seconds: int = Field(default=0, ge=0)
    # NFR-AI-QUAL17: voice = answer la ban ghi STT (doi thuat ngu phien am truoc khi cham); stt_confidence do
    # dich vu STT tra (0-1), thap hon nguong thi luot khong duoc cham
    answer_source: Literal["text", "voice"] = "text"
    stt_confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _typed_answer_not_empty(self):
        if self.answer_source == "text" and not self.answer:
            raise ValueError("answer khong duoc rong")
        return self


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
