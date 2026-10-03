"""Pydantic models cho contract REST cua ai-service (snake_case).

Contract: docs/architecture/ai-integration.md muc 5.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

AgentDecision = Literal["deepen", "switch_topic", "keep_difficulty"]
AnswerSignal = Literal["weak", "ok", "strong"]


class InterviewContext(BaseModel):
    category: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    candidate_skills: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None


class CriteriaScores(BaseModel):
    technical_accuracy: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)
    extensibility: float = Field(ge=0, le=10)


class Metadata(BaseModel):
    model_version: str
    processing_time_ms: int


# --- /api/start ---
class StartRequest(BaseModel):
    session_id: str = Field(min_length=1)
    context: InterviewContext


class QuestionMetadata(BaseModel):
    topic: str
    difficulty: str
    expected_topics: List[str]


class StartResponse(BaseModel):
    first_question: str
    question_metadata: QuestionMetadata


# --- /api/next-turn ---
class TurnHistory(BaseModel):
    turn_number: int
    question: str
    answer: str
    answer_signal: Optional[AnswerSignal] = None
    agent_decision: Optional[AgentDecision] = None


class NextTurnRequest(BaseModel):
    session_id: str = Field(min_length=1)
    turn_number: int = Field(ge=1)
    question: str
    answer: str
    history: List[TurnHistory] = Field(default_factory=list)
    context: InterviewContext


class NextTurnResponse(BaseModel):
    next_question: str
    agent_decision: AgentDecision
    answer_signal: AnswerSignal
    reasoning: str
    metadata: Metadata


# --- /api/finalize ---
class FinalizeTurn(BaseModel):
    turn_number: int
    question: str
    answer: str


class FinalizeRequest(BaseModel):
    session_id: str = Field(min_length=1)
    context: InterviewContext
    turns: List[FinalizeTurn] = Field(min_length=1)


class TurnEvaluation(BaseModel):
    turn_number: int
    scores: CriteriaScores
    comment: str


class FinalizeResponse(BaseModel):
    turns: List[TurnEvaluation]
    overall_score: float
    criteria_averages: CriteriaScores
    strengths: List[str]
    improvements: List[str]
    summary: str
    metadata: Metadata


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict = Field(default_factory=dict)
