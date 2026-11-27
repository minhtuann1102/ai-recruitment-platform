"""Kich ban golden (plan 261127-1517, phase 01): phu cac nhanh cua next_turn() truoc khi boc LangGraph.

Moi kich ban chi dung mock / fake (khong LLM, khong ai_db that) nen chay lai cho ra cung trace. Danh sach nhanh:
ask_main / follow_up / hint / next_topic / next_phase / wrap_up -> done, 409 sau done, low_performance, two_dont_know,
voice (no_speech 422, reask, unclear 422), forced end (qua han cung), cau trong kho (qa_id, question_source = bank),
policy hybrid + doi topic (swap). Patch Evaluator tai `app.turn_engine.get_evaluator`: phase 02 doi cho goi thi doi
`EVALUATOR_SEAM` o day.
"""
from typing import Callable, Dict

import pytest
from fastapi.testclient import TestClient

import app.plan_snippets as plan_snippets
from app.main import app
from app.rag.circuit_breaker import CircuitBreaker
from tests.golden_turns.golden_session_runner import run_session
from tests.test_policy_hybrid_turn_engine import ProposalEvaluator
from tests.test_question_bank import FakeRetriever
from tests.test_replan import sw, v10
from tests.test_replan_turn_engine import DONE_OK

EVALUATOR_SEAM = "app.turn_engine.get_evaluator"


def strong(topic) -> str:
    """Tra loi du moi key point (mock Evaluator cham cao)."""
    return ". ".join(topic["key_points"] * 2) + ". " + "chi tiết " * 12 if topic else "Cảm ơn ạ, em không có câu hỏi."


def partial(topic) -> str:
    """Chi neu key point dau, ngan: mock Evaluator thieu y -> follow_up / hint."""
    return f"Em nghĩ là {topic['key_points'][0]}." if topic and topic.get("key_points") else "Dạ em chưa rõ ạ."


def _text(fn):
    return lambda step, caller, topic: {"answer": fn(topic)}


def _use_fake_rag(mp: pytest.MonkeyPatch) -> None:
    """RAG gia: moi topic technical co 2 cau trong kho + dap an chuan (khong ai_db)."""
    mp.setattr(plan_snippets, "_loaded", True)
    mp.setattr(plan_snippets, "_retriever", FakeRetriever())
    mp.setattr(plan_snippets, "_config_error", None)
    mp.setattr(plan_snippets, "_breaker", CircuitBreaker(60))


def text_strong_full_session(client, mp):
    return run_session(client, "g-strong", "java_backend", "junior", _text(strong), finalize=True, after_end=1)


def text_partial_answers_mid(client, mp):
    return run_session(client, "g-partial", "python_backend", "middle", _text(partial), finalize=True)


def text_dont_know_two_dont_know(client, mp):
    return run_session(client, "g-weak", "nodejs_backend", "junior", lambda s, c, t: {"answer": "Em không biết ạ."},
                       finalize=True)


def text_weak_senior_low_performance(client, mp):
    """Senior tra loi lac de lien tuc: 3 topic technical yeu -> low_performance_stop (chi middle / senior)."""
    return run_session(client, "g-low", "java_backend", "senior",
                       lambda s, c, t: {"answer": "Dạ em nghĩ cái này tùy dự án, em thường hỏi đồng nghiệp ạ."},
                       finalize=True)


def voice_reask_and_rejects(client, mp):
    """Luot 1 text; luot 2: voice rong (422 no_speech) -> do tin cay thap (reask) -> thap lan nua (422 unclear) ->
    go chat; sau do voice tot vai luot."""
    script = [{"answer": "Em là lập trình viên Java hai năm kinh nghiệm."},
              {"answer": "", "answer_source": "voice", "stt_confidence": 0.9},
              {"answer": "ừm ờ cái đó", "answer_source": "voice", "stt_confidence": 0.2},
              {"answer": "ừm ờ cái đó", "answer_source": "voice", "stt_confidence": 0.2}]

    def answer_for(step, caller, topic):
        if step < len(script):
            return script[step]
        if step == len(script):
            return {"answer": strong(topic)}
        return {"answer": strong(topic), "answer_source": "voice", "stt_confidence": 0.95} if step < 9 else None
    return run_session(client, "g-voice", "java_backend", "junior", answer_for)


def time_forced_end(client, mp):
    """Luot 2 bao da qua xa thoi luong: forced end, khong hoi them."""
    def answer_for(step, caller, topic):
        return {"answer": strong(topic)} if step == 0 else \
            {"answer": strong(topic), "elapsed_seconds": 99999} if step == 1 else None
    return run_session(client, "g-forced", "java_backend", "junior", answer_for, after_end=1)


def bank_questions_fake_rag(client, mp):
    _use_fake_rag(mp)
    return run_session(client, "g-bank", "java_backend", "junior", _text(strong), max_steps=8)


def hybrid_policy_with_swap(client, mp):
    """POLICY_MODE=hybrid + REPLAN_ENABLED: Evaluator de xuat next_topic + doi t4 -> alt1 (nhu test_replan_turn_engine)."""
    mp.setenv("POLICY_MODE", "hybrid")
    mp.setenv("REPLAN_ENABLED", "true")
    evaluator = ProposalEvaluator(DONE_OK, v10(sw("t4", "alt1")))
    mp.setattr(EVALUATOR_SEAM, lambda: evaluator)
    return run_session(client, "g-hybrid", "java_backend", "junior", _text(strong),
                       start_extra={"duration_minutes": 30}, max_steps=12)


SCENARIOS: Dict[str, Callable] = {f.__name__: f for f in (
    text_strong_full_session, text_partial_answers_mid, text_dont_know_two_dont_know,
    text_weak_senior_low_performance, voice_reask_and_rejects,
    time_forced_end, bank_questions_fake_rag, hybrid_policy_with_swap)}


def run_scenario(name: str) -> Dict:
    """Chay mot kich ban voi env / patch rieng (tra lai nhu cu sau khi chay)."""
    with pytest.MonkeyPatch.context() as mp:
        return SCENARIOS[name](TestClient(app), mp)
