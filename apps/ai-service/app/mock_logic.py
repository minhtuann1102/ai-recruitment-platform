"""Logic mock cho ai-service (Sprint 0). Se thay bang Planner/Interviewer/Evaluator that."""
import random
import time
from typing import List

from .schemas import (
    CriteriaScores,
    FinalizeRequest,
    FinalizeResponse,
    Metadata,
    NextTurnRequest,
    NextTurnResponse,
    StartRequest,
    StartResponse,
    QuestionMetadata,
    TurnEvaluation,
)

MODEL_VERSION = "mock-v1"

MOCK_QUESTIONS = [
    "Giai thich su khac biet giua process va thread?",
    "Design pattern nao ban thuong dung nhat? Tai sao?",
    "Lam sao de toi uu hoa query SQL chay cham?",
    "Giai thich CAP theorem va ap dung vao thiet ke he thong?",
    "Event-driven architecture la gi? Khi nao nen dung?",
]

_DECISIONS = ["deepen", "switch_topic", "keep_difficulty"]
_SIGNALS = ["weak", "ok", "strong"]


def _meta(started: float) -> Metadata:
    return Metadata(
        model_version=MODEL_VERSION,
        processing_time_ms=int((time.perf_counter() - started) * 1000),
    )


def mock_start(req: StartRequest) -> StartResponse:
    return StartResponse(
        first_question=random.choice(MOCK_QUESTIONS),
        question_metadata=QuestionMetadata(
            topic=req.context.category,
            difficulty=req.context.difficulty,
            expected_topics=["concept", "example", "trade-off"],
        ),
    )


def mock_next_turn(req: NextTurnRequest) -> NextTurnResponse:
    started = time.perf_counter()
    asked = {h.question for h in req.history} | {req.question}
    pool = [q for q in MOCK_QUESTIONS if q not in asked] or MOCK_QUESTIONS
    return NextTurnResponse(
        next_question=random.choice(pool),
        agent_decision=random.choice(_DECISIONS),
        answer_signal=random.choice(_SIGNALS),
        reasoning="Mock: random decision for testing.",
        metadata=_meta(started),
    )


def _mock_scores() -> CriteriaScores:
    return CriteriaScores(
        technical_accuracy=round(random.uniform(5.0, 9.0), 1),
        relevance=round(random.uniform(5.0, 9.0), 1),
        completeness=round(random.uniform(4.0, 8.0), 1),
        extensibility=round(random.uniform(4.0, 8.0), 1),
    )


def _avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 1)


def mock_finalize(req: FinalizeRequest) -> FinalizeResponse:
    started = time.perf_counter()
    evaluations = [
        TurnEvaluation(
            turn_number=t.turn_number,
            scores=_mock_scores(),
            comment=f"Mock comment cho cau {t.turn_number}.",
        )
        for t in req.turns
    ]
    averages = CriteriaScores(
        technical_accuracy=_avg([e.scores.technical_accuracy for e in evaluations]),
        relevance=_avg([e.scores.relevance for e in evaluations]),
        completeness=_avg([e.scores.completeness for e in evaluations]),
        extensibility=_avg([e.scores.extensibility for e in evaluations]),
    )
    overall = _avg(
        [
            averages.technical_accuracy,
            averages.relevance,
            averages.completeness,
            averages.extensibility,
        ]
    )
    return FinalizeResponse(
        turns=evaluations,
        overall_score=overall,
        criteria_averages=averages,
        strengths=["Mock: nam vung kien thuc co ban"],
        improvements=["Mock: can bo sung chieu sau"],
        summary="Mock: ket qua tong hop de test.",
        metadata=_meta(started),
    )
