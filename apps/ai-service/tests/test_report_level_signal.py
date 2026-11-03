"""Co "vuot level" trong bao cao (docs 05 muc Goi y level): bien tung dieu kien, Reporter LLM khong lam mat co."""
import asyncio

import pytest
from test_report_failure_signals import session  # noqa: F401  (fixture: phien junior tra loi tot)
from test_reporter import make, output

from app.report_level_signal import level_signal
from app.report_scoring import build_report, scored_turns


def tuned(req, score=9.0, ceiling_turns=3, difficulty=4, level=None):
    """Moi luot duoc cham dat `score`; `ceiling_turns` luot dau o do kho `difficulty`, con lai o muc 2."""
    turns, n = [], 0
    for t in req.turns:
        if t.evaluation and t.phase != "wrap_up":
            d = difficulty if n < ceiling_turns else 2
            t = t.model_copy(update={"difficulty": d,
                                     "evaluation": t.evaluation.model_copy(update={"turn_score_10": score})})
            n += 1
        turns.append(t)
    return req.model_copy(update={"turns": turns, "level": level or req.level})


def test_strong_junior_at_ceiling_is_flagged(session):  # noqa: F811
    req = tuned(session)
    rep = build_report(req)
    assert rep["session"]["confidence"] != "low" and rep["overall"]["verdict"] == "exceeds"
    sig = rep["level_signal"]
    assert sig["type"] == "above_level" and sig["current_level"] == "junior" and sig["suggested_level"] == "middle"
    assert sig["evidence_turns"] == [t.turn_number for t in scored_turns(req)][:3]
    assert "middle" in sig["note"]


@pytest.mark.parametrize("kw", [
    {"ceiling_turns": 2},               # chua du luot o tran
    {"difficulty": 3},                  # diem cao nhung duoi tran (junior tran = 4)
    {"level": "senior", "difficulty": 5},  # khong con level cao hon
    {"score": 8.4},                     # chua toi exceeds
])
def test_not_flagged(session, kw):  # noqa: F811
    assert build_report(tuned(session, **kw))["level_signal"] is None


def test_fresher_ceiling_is_lower(session):  # noqa: F811
    sig = build_report(tuned(session, difficulty=3, level="fresher"))["level_signal"]
    assert sig and sig["suggested_level"] == "junior"


def test_low_confidence_or_unscored_is_not_flagged(session):  # noqa: F811
    scored = scored_turns(tuned(session))
    assert level_signal("junior", scored, 9.0, "low") is None
    assert level_signal("junior", scored, None, "medium") is None


def test_ceiling_turn_with_weak_score_does_not_count(session):  # noqa: F811
    req = tuned(session)
    first = scored_turns(req)[0].turn_number
    turns = [t.model_copy(update={"evaluation": t.evaluation.model_copy(update={"turn_score_10": 6.0})})
             if t.turn_number == first else t for t in req.turns]
    assert build_report(req.model_copy(update={"turns": turns}))["level_signal"] is None  # con 2 luot tot o tran


def test_llm_reporter_keeps_level_signal(session):  # noqa: F811
    req = tuned(session)
    reporter, _ = make([output(req)])
    rep = asyncio.run(reporter.report(req))
    assert rep["level_signal"] == build_report(req)["level_signal"] and rep["level_signal"] is not None
