"""Mot request RAG loi khong duoc lam hong cac phien khac: ngat can loi lap lai, start giu topic da xong, dang ngat
van dung BM25 + cache dap an (do 30/10: 1 rag_timeout -> 42 request mat RAG, 4/10 phien mat ca kho)."""
import asyncio
import logging

import pytest
from test_rag_turn_retrieval import HASHMAP, TOPIC_ID, retriever, run

from app import plan_snippets as ps
from app import turn_reference_snippets as trs
from app.llm.usage import UsageCollector
from app.mock_planner import build_plan, load_track
from app.models_interview import NextTurnRequest, StartRequest
from app.rag.circuit_breaker import CircuitBreaker
from app.turn_engine import next_turn, start_session
from tests.test_question_bank import CaptureEvaluator, finish_turn


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


@pytest.fixture(autouse=True)
def _sql_on(monkeypatch):
    monkeypatch.setattr(trs, "_sql_off_until", 0.0)


def use(monkeypatch, r, breaker):
    for name, value in (("_loaded", True), ("_retriever", r), ("_config_error", None), ("_breaker", breaker)):
        monkeypatch.setattr(ps, name, value)


def test_one_failure_does_not_open_breaker_but_repeated_failures_do(caplog):
    clock = Clock()
    breaker = CircuitBreaker(60, clock)
    breaker.record(["rag_timeout"])
    breaker.record(["rag_bank_failed"])
    assert not breaker.is_open() and breaker.last_errors == ["rag_bank_failed"]
    with caplog.at_level(logging.WARNING, "ai_service.rag"):
        breaker.record(["rag_timeout"])
    assert breaker.is_open() and "rag_circuit_open" in caplog.text
    clock.now += 61
    assert not breaker.is_open()
    breaker.record(["rag_timeout"])  # dem lai tu dau sau khi dong
    assert not breaker.is_open()


def test_outage_at_low_traffic_still_opens_breaker():
    clock = Clock()
    breaker = CircuitBreaker(60, clock)
    for _ in range(2):
        breaker.record(["rag_timeout"])
        clock.now += 16
        assert not breaker.is_open()
    breaker.record(["rag_timeout"])
    assert breaker.is_open()


def test_failures_while_open_do_not_extend_or_replace_the_cause():
    clock = Clock()
    breaker = CircuitBreaker(60, clock, threshold=1)
    breaker.record(["rag_timeout"])
    clock.now += 50
    breaker.record(["rag_bank_failed"])
    assert breaker.remaining_s() == 10 and breaker.last_errors == ["rag_timeout"]


def test_failures_outside_window_and_soft_errors_do_not_count():
    clock = Clock()
    breaker = CircuitBreaker(60, clock)
    for _ in range(5):
        breaker.record(["rag_timeout"])
        clock.now += 61  # hon 1 phut mot loi: chua bao gio co 3 loi trong 120 s
        assert not breaker.is_open()
    for _ in range(5):
        breaker.record(["rag_hybrid_partial", "rag_start_partial", "rag_memory_only", "rag_turn_failed"])
    assert not breaker.is_open()


def slow_for(monkeypatch, r, slow_topic):
    real = r.plan_snippets

    async def plan_snippets(*, topic_id, **kwargs):
        if topic_id == slow_topic:
            await asyncio.sleep(5)
        return await real(topic_id=topic_id, **kwargs)

    monkeypatch.setattr(r, "plan_snippets", plan_snippets)
    monkeypatch.setattr(ps, "SNIPPET_DEADLINE_S", 0.2)


def test_start_keeps_finished_topics_when_one_topic_misses_the_deadline(monkeypatch):
    plan = build_plan("java_backend", "junior", 20, None)
    technical = [t for ph in plan.phases if ph.phase == "technical" for t in ph.topics]
    fast = next(t for t in technical if t.catalog_ref == TOPIC_ID)
    slow = next(t for t in technical if t.id != fast.id)
    r, collector, breaker = retriever(), UsageCollector(), CircuitBreaker(60, threshold=1)
    r.question_bank = False  # repo gia khong co list_bank
    use(monkeypatch, r, breaker)
    slow_for(monkeypatch, r, slow.catalog_ref)
    out = run(ps.attach_reference_snippets(plan, load_track("java_backend"), r, collector))
    topics = {t.id: t for ph in out.phases for t in ph.topics}
    assert HASHMAP in topics[fast.id].reference_snippets and topics[fast.id].reference_sources
    assert topics[slow.id].reference_snippets == [] and topics[slow.id].bank_questions == []
    assert collector.rag_errors == ["rag_start_partial"]
    assert ps.rag_status(collector)["status"] == "degraded"
    ps.note_rag_errors(collector)
    assert not breaker.is_open()


def test_one_failing_topic_does_not_lose_other_topics_or_the_start(monkeypatch):
    plan = build_plan("java_backend", "junior", 20, None)
    technical = [t for ph in plan.phases if ph.phase == "technical" for t in ph.topics]
    fast = next(t for t in technical if t.catalog_ref == TOPIC_ID)
    broken = next(t for t in technical if t.id != fast.id)
    r, collector = retriever(), UsageCollector()
    r.question_bank = False
    real = r.plan_snippets

    async def plan_snippets(*, topic_id, **kwargs):
        if topic_id == broken.catalog_ref:
            raise ValueError("loi ngoai try cua retriever")
        return await real(topic_id=topic_id, **kwargs)

    monkeypatch.setattr(r, "plan_snippets", plan_snippets)
    out = run(ps.attach_reference_snippets(plan, load_track("java_backend"), r, collector))
    topics = {t.id: t for ph in out.phases for t in ph.topics}
    assert HASHMAP in topics[fast.id].reference_snippets and topics[broken.id].reference_snippets == []
    assert collector.rag_errors == ["rag_retrieve_failed"]


def test_cancelled_start_cancels_topic_tasks(monkeypatch):
    cancelled = []
    r = retriever()

    async def hang(**_):
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    monkeypatch.setattr(r, "plan_snippets", hang)

    async def main():
        plan = build_plan("java_backend", "junior", 20, None)
        task = asyncio.ensure_future(ps.attach_reference_snippets(plan, load_track("java_backend"), r))
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.01)
        assert cancelled  # ngay trong loop: teardown cua asyncio.run cung huy task, assert sau do khong chung minh gi

    asyncio.run(main())


def test_open_breaker_keeps_bm25_for_the_turn_without_reading_ai_db(monkeypatch):
    r, evaluator = retriever(), CaptureEvaluator()
    r.question_bank = False
    res = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior", duration_minutes=20),
                            retriever=r))
    target = next(t.id for ph in res.plan.phases for t in ph.topics if t.catalog_ref == TOPIC_ID)
    finish_turn(res, "Giới thiệu bản thân?", "ai")
    for _ in range(6):
        if res.turn.topic_id == target:
            break
        req = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=res.plan, state=res.state,
                              turn_number=res.turn.turn_number, question=res.question, answer="Em làm dự án Java.",
                              elapsed_seconds=60 * res.turn.turn_number)
        res = run(next_turn(req, evaluator=evaluator, retriever=r))
        finish_turn(res, "Câu AI tự đặt?", "ai")
    for t in (t for ph in res.plan.phases for t in ph.topics if t.id == target):
        t.reference_snippets = []  # bo chunk topic da gan luc start de chunk duoi chac chan tu truy hoi theo luot
    breaker = CircuitBreaker(60, threshold=1)
    breaker.record(["rag_timeout"])
    use(monkeypatch, r, breaker)
    collector = UsageCollector()
    req = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=res.plan, state=res.state,
                          turn_number=res.turn.turn_number, question="HashMap xử lý va chạm như thế nào?",
                          answer="Em nghĩ dùng bucket", elapsed_seconds=60 * res.turn.turn_number)
    before = len(r.repo.calls)
    run(next_turn(req, evaluator=evaluator, collector=collector))
    assert HASHMAP in evaluator.inputs[-1].turn_snippets and len(r.repo.calls) == before
    assert collector.rag_errors == ["rag_memory_only"]
    status = ps.rag_status(collector)
    assert status["status"] == "degraded" and "rag_unavailable" not in str(status)


def bank_turn(monkeypatch, r, qa_id):
    """next_turn cua mot cau tu kho khi mach dang mo; tra evaluator de xem dap an chuan nhan duoc."""
    evaluator, collector = CaptureEvaluator(), UsageCollector()
    r.question_bank = False
    res = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior", duration_minutes=20),
                            retriever=r))
    finish_turn(res, "Giới thiệu bản thân?", "ai")
    res.state.current_qa_id = qa_id
    breaker = CircuitBreaker(60, threshold=1)
    breaker.record(["rag_timeout"])
    use(monkeypatch, r, breaker)
    req = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=res.plan, state=res.state,
                          turn_number=res.turn.turn_number, question=res.question, answer="Em làm dự án Java.",
                          elapsed_seconds=60)
    before = len(r.repo.calls)
    run(next_turn(req, evaluator=evaluator, collector=collector))
    return evaluator, collector, len(r.repo.calls) - before


def test_open_breaker_uses_cached_answer_key_and_skips_database(monkeypatch):
    r = retriever()
    r.answers.put("q1", "dap an")
    evaluator, collector, repo_calls = bank_turn(monkeypatch, r, "q1")
    assert evaluator.inputs[-1].reference_answer == "dap an"
    assert repo_calls == 0 and collector.rag_errors == ["rag_memory_only"]


def test_open_breaker_with_cache_miss_grades_without_answer_key_and_skips_database(monkeypatch):
    evaluator, collector, repo_calls = bank_turn(monkeypatch, retriever(), "khong-co")
    assert evaluator.inputs[-1].reference_answer == ""
    assert repo_calls == 0 and collector.rag_errors == ["rag_memory_only"]


def test_start_during_open_breaker_still_reports_error(monkeypatch):
    breaker = CircuitBreaker(60, threshold=1)
    breaker.record(["rag_timeout"])
    use(monkeypatch, object(), breaker)
    assert ps.get_retriever() is None and ps.rag_status(UsageCollector())["errors"] == ["rag_cooldown"]
