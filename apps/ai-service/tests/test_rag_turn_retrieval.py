"""Phase 02: truy hoi theo luot (BM25 theo cau hoi + cau tra loi, tang diem topic_id), noi vao next_turn.
Khong can DB."""
import asyncio
import time

import pytest

import app.plan_snippets as ps
import app.turn_reference_snippets as trs
from app import turn_engine
from app.agents.evaluator import EvaluationInput, build_messages
from app.llm.usage import UsageCollector
from app.mock_planner import build_plan
from app.models_interview import NextTurnRequest, StartRequest
from app.policy import Decision
from app.rag.bm25_index import Bm25Index
from app.rag.circuit_breaker import CircuitBreaker
from app.rag.retriever import Retriever
from app.turn_engine import finish_turn, next_turn, start_session
from app.turn_reference_snippets import turn_snippets
from tests.fakes.fake_knowledge_repo import FakeEmbed, FakeKnowledgeRepo, qa
from tests.test_question_bank import CaptureEvaluator

TOPIC_ID = "java.core.collections-hashmap"
HASHMAP = ("HashMap xử lý va chạm thế nào?\n\nKhi hai key cùng bucket, HashMap dùng danh sách liên kết, "
           "từ Java 8 là cây đỏ đen.")
RESIZE = "Khi nào HashMap resize?\n\nKhi số phần tử vượt load factor 0.75 thì HashMap gấp đôi bảng và rehash."
OTHER = "Spring Bean scope là gì?\n\nSingleton, prototype, request, session."


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _sql_on(monkeypatch):
    monkeypatch.setattr(trs, "_sql_off_until", 0.0)  # cooldown SQL topic_id la trang thai process


class SlowRepo(FakeKnowledgeRepo):
    """Tra topic_id treo va bo qua lenh huy (nhu psycopg cho server xac nhan huy)."""

    async def list_by_topic_id(self, topic_id, difficulty, limit):
        self.calls.append(("topic", topic_id))
        try:
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            await asyncio.sleep(0.3)  # > TURN_DEADLINE_S cua test: wait_for khong shield se cho het
        return []


def topic():
    plan = build_plan("java_backend", "junior", 20, None)
    return next(t for ph in plan.phases for t in ph.topics if t.catalog_ref == TOPIC_ID)


def retriever(by_topic=(), fail=None, turn=True, loaded=True, repo_cls=FakeKnowledgeRepo, textbook=False):
    # difficulty None: khop moi muc (do kho thich ung doi giua cac luot)
    corpus = [qa("hm", TOPIC_ID, HASHMAP, None), qa("rs", "x", RESIZE, None), qa("sp", "y", OTHER, None)]
    repo = repo_cls(by_topic=list(by_topic), fail=fail, lexical=corpus)
    r = Retriever(repo, FakeEmbed(), hybrid=True, turn_retrieval=turn)
    r.textbook = textbook
    if loaded:  # nhu da nap xong: /start khong nap lai (fail cua repo gia lam hong ca lan nap corpus)
        r.hybrid.bm25._index, r.hybrid.bm25._loaded_at = Bm25Index(corpus), time.monotonic()
    return r


def chunks(r, *, phase="technical", t=None, key=False, collector=None, difficulty=1,
           question="HashMap xử lý va chạm như thế nào?", answer="Em nghĩ HashMap dùng bucket, khi trùng thì resize"):
    return run(turn_snippets(r, "java_backend", phase=phase, topic=t or topic(), difficulty=difficulty,
                             question=question, answer=answer, has_answer_key=key, collector=collector))


def snippets(r, **kw):
    return chunks(r, **kw).texts


def test_finds_chunks_for_question_and_answer_boosted_by_topic_and_skips_known():
    out = snippets(retriever(by_topic=[qa("hm", TOPIC_ID, HASHMAP, None)]))
    assert out[0] == HASHMAP and RESIZE in out and OTHER not in out  # topic_id tang diem, chunk lac de bi loai
    t = topic()
    t.reference_snippets = [HASHMAP]  # da co trong snippet cua topic: khong dua lai
    assert HASHMAP not in snippets(retriever(), t=t)
    t.reference_snippets = [HASHMAP[:40] + " ..."]  # snippet cuoi bi cat theo ngan sach token van tinh la trung
    assert HASHMAP not in snippets(retriever(), t=t)


def test_hint_source_is_only_a_chunk_of_the_same_topic():
    assert chunks(retriever()).hint == HASHMAP
    off = chunks(retriever(), question="Khi nào resize?", answer="load factor")
    assert off.texts == [RESIZE] and off.hint == ""  # BM25 bat chunk topic khac: khong dung lam goi y


def test_skipped_when_answer_key_intro_flag_off_or_corpus_not_loaded():
    assert snippets(retriever(), key=True) == []  # cau tu kho: da co dap an chuan
    assert snippets(retriever(), phase="intro") == []
    assert snippets(retriever(turn=False)) == []
    assert snippets(retriever(loaded=False)) == []  # khong cho nap corpus
    assert snippets(retriever(), difficulty=0) == []  # state hong: bo qua, khong bao loi


def test_scenario_searches_textbook_only_without_topic_sql():
    assert snippets(retriever(), phase="scenario") == []  # textbook tat: khong co nguon nao cho scenario
    r = retriever(textbook=True)
    assert snippets(r, phase="scenario") == []  # corpus test chi co interview_qa
    assert not [c for c in r._repo.calls if c[0] != "corpus"]


def test_hung_topic_sql_returns_bm25_on_deadline_then_cools_down(monkeypatch):
    monkeypatch.setattr(trs, "TURN_DEADLINE_S", 0.05)
    r, collector = retriever(repo_cls=SlowRepo), UsageCollector()

    async def two_turns():
        started = time.perf_counter()
        first = await turn_snippets(r, "java_backend", phase="technical", topic=topic(), difficulty=1,
                                    question="HashMap va chạm?", answer="bucket", has_answer_key=False,
                                    collector=collector)
        took = time.perf_counter() - started
        second = await turn_snippets(r, "java_backend", phase="technical", topic=topic(), difficulty=1,
                                     question="HashMap va chạm?", answer="bucket", has_answer_key=False)
        return first, took, second

    first, took, second = asyncio.run(two_turns())
    assert HASHMAP in first.texts and took < 0.25 and collector.rag_errors == ["rag_turn_failed"]
    assert HASHMAP in second.texts and len([c for c in r._repo.calls if c[0] == "topic"]) == 1  # cooldown: chi BM25


def test_topic_sql_failure_keeps_bm25_results_as_soft_error(monkeypatch):
    collector = UsageCollector()
    out = snippets(retriever(fail=OSError("db")), collector=collector)
    assert HASHMAP in out and collector.rag_errors == ["rag_turn_failed"]
    breaker = CircuitBreaker(60)
    for name, value in (("_loaded", True), ("_retriever", object()), ("_config_error", None), ("_breaker", breaker)):
        monkeypatch.setattr(ps, name, value)
    assert ps.rag_status(collector)["status"] == "degraded"
    ps.note_rag_errors(collector)
    assert not breaker.is_open()


def test_evaluator_sees_topic_then_turn_snippets():
    t = topic()
    t.reference_snippets = ["topic snippet"]
    inp = EvaluationInput(level="junior", phase="technical", topic=t, difficulty=1, turn_kind="main", turn_number=2,
                          question="q", answer="a", turn_snippets=["turn chunk"])
    user = build_messages("SYS", inp)[1]["content"]
    assert user.index("topic snippet") < user.index("turn chunk")


def test_next_turn_passes_turn_chunks_to_evaluator_and_hint(monkeypatch):
    r, evaluator = retriever(), CaptureEvaluator()
    r.question_bank = False  # khong co cau tu kho: luot technical la cau AI tu dat, khong co dap an chuan
    res = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior", duration_minutes=20),
                            retriever=r))
    target = next(t.id for ph in res.plan.phases for t in ph.topics if t.catalog_ref == TOPIC_ID)
    finish_turn(res, "Giới thiệu bản thân?", "ai")
    for _ in range(6):  # qua intro toi topic HashMap
        if res.turn.topic_id == target:
            break
        req = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=res.plan, state=res.state,
                              turn_number=res.turn.turn_number, question=res.question, answer="Em làm dự án Java.",
                              elapsed_seconds=60 * res.turn.turn_number)
        res = run(next_turn(req, evaluator=evaluator, retriever=r))
        finish_turn(res, "Câu AI tự đặt?", "ai")
    assert res.turn.topic_id == target and not res.state.current_qa_id
    for t in (t for ph in res.plan.phases for t in ph.topics if t.id == target):
        t.reference_snippets = []  # luc start BM25 da gan chunk HashMap vao snippet topic (luot sau se bo vi trung)
    monkeypatch.setattr(turn_engine, "decide", lambda *a, **k: Decision("hint", 0, "va chạm", "test"))
    req = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=res.plan, state=res.state,
                          turn_number=res.turn.turn_number, question="HashMap xử lý va chạm như thế nào?",
                          answer="Em nghĩ dùng bucket", elapsed_seconds=60 * res.turn.turn_number)
    h = run(next_turn(req, evaluator=evaluator, retriever=r))
    got = evaluator.inputs[-1].turn_snippets
    assert HASHMAP in got and h.spec.action == "hint" and h.spec.reference_answer == HASHMAP
