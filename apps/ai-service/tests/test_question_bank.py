"""Ngan hang cau hoi tu kho interview_qa: chon cau, gan vao plan, Interviewer dien dat lai, Evaluator nhan dap an
chuan theo qa_id cua cau vua hoi, cau du phong lay nguyen van cau trong kho."""
import asyncio

from app.agents.evaluator import EvaluationInput, EvaluatorOutput, build_messages as eval_messages, postcheck
from app.agents.interviewer import QuestionSpec, build_messages, fallback_question
from app.agents.planner import MockPlanner
from app.models_interview import BankQuestion, Evaluation, NextTurnRequest, StartRequest
from app.rag.question_bank import AnswerCache, BankEntry, pick, plain, rank, spoken_ok
from app.rag.retriever import Retriever
from app.turn_engine import finish_turn, next_turn, start_session
from fakes.fake_knowledge_repo import FakeEmbed, FakeKnowledgeRepo, qa


def run(coro):
    return asyncio.run(coro)


def entry(qa_id, question, difficulty="easy"):
    return BankEntry(qa_id, question, difficulty, f"{question}\n\nĐáp án {qa_id}.")


def test_spoken_filter_rank_and_pick():
    assert spoken_ok("HashMap xử lý collision thế nào?")
    assert not spoken_ok("Giải thích đoạn sau\n```yaml\nport: 1\n```") and not spoken_ok("x" * 201)
    entries = [entry("a", "Lambda trong Java là gì?"), entry("b", "HashMap resize khi nào?", "hard"),
               entry("c", "HashMap xử lý collision thế nào?"), entry("d", "Code:\n```x```")]
    ranked = rank(entries, ["Java Collections và HashMap", "collision và treeification"], "easy", 3,
                  generic=["Java Backend Developer"])
    assert [e.qa_id for e in ranked] == ["c", "b"]  # bo cau co code va cau chi trung "Java"
    ranked = rank(entries, ["Java Collections và HashMap", "collision"], "easy", 3)  # khong co tu chung cua track
    assert [e.qa_id for e in ranked] == ["c", "a", "b"]  # dung do kho truoc, roi cau sat topic hon
    assert [e.qa_id for e in rank(entries, ["HashMap", "collision"], "hard", 3)][0] == "b"
    bank = [BankQuestion(qa_id=e.qa_id, question=e.question, difficulty=e.difficulty) for e in ranked]
    assert pick(bank, [], "hard").qa_id == "b" and pick(bank, ["b"], "hard") is None  # easy khi dang hard: bo
    assert pick(bank, ["c"], "easy").qa_id == "a" and pick(bank, ["c", "a"], "medium").qa_id == "b"
    assert pick(bank, ["a", "b", "c"], "easy") is None
    assert plain("`HashMap` dùng **hashCode** thế nào?") == "HashMap dùng hashCode thế nào?"


def test_answer_cache_is_lru_and_truncated():
    cache = AnswerCache(size=2)
    cache.put("a", "x" * 5000)
    cache.put("b", "B")
    cache.get("a")
    cache.put("c", "C")
    assert cache.get("b") is None and len(cache.get("a")) == 1800 and cache.get("c") == "C"


class BankRepo(FakeKnowledgeRepo):
    def __init__(self, entries, **kw):
        super().__init__(**kw)
        self.entries = entries

    async def list_bank(self, topic_id, difficulty, limit):
        self.calls.append(("bank", topic_id, difficulty, limit))
        if self.fail:
            raise self.fail
        return self.entries[:limit]


def test_retriever_bank_caches_answers_and_reads_db_on_miss():
    repo = BankRepo([entry("q1", "HashMap là gì?")], by_topic=[qa("q9", "t", content="Q9?\n\nĐáp án 9")])
    r = Retriever(repo, FakeEmbed())
    assert [e.qa_id for e in run(r.bank_for_topic("t", 2, ["HashMap"]))] == ["q1"]
    assert run(r.answer_key("q1")) == "HashMap là gì?\n\nĐáp án q1."  # tu cache, khong goi DB
    assert run(r.answer_key("q9")) == "Q9?\n\nĐáp án 9" and ("pair", "q9") in repo.calls  # truot cache
    assert run(Retriever(BankRepo([], fail=OSError()), FakeEmbed()).bank_for_topic("t", 2, [])) == []


class FakeRetriever:
    def __init__(self):
        self.asked = []

    async def plan_snippets(self, **_):
        return []

    async def bank_for_topic(self, topic_id, difficulty, terms, generic=(), n=3):
        return [entry(f"{topic_id}#1", f"`{topic_id}` hoạt động thế nào?"), entry(f"{topic_id}#2", "Câu thứ hai?")]

    async def answer_key(self, qa_id):
        self.asked.append(qa_id)
        return f"Đáp án chuẩn {qa_id}"


class CaptureEvaluator:
    def __init__(self):
        self.inputs = []

    async def evaluate(self, inp, collector=None):
        self.inputs.append(inp)
        return Evaluation(turn_number=inp.turn_number, answer_type="answered",
                          scores={k: 2 for k in ("technical_accuracy", "completeness", "extensibility", "relevance")},
                          scores_10={k: 5.0 for k in ("technical_accuracy", "completeness", "extensibility",
                                                      "relevance")}, turn_score_10=5.0)


def test_engine_asks_bank_question_and_evaluator_gets_answer_key():
    retr, evaluator = FakeRetriever(), CaptureEvaluator()
    req = StartRequest(session_id="s", track="java_backend", level="junior", duration_minutes=20)
    r = run(start_session(req, planner=MockPlanner(), retriever=retr))
    tech = [t for ph in r.plan.phases if ph.phase == "technical" for t in ph.topics]
    assert tech and all(t.bank_questions for t in tech)
    assert not any(t.bank_questions for ph in r.plan.phases if ph.phase != "technical" for t in ph.topics)
    assert tech[0].bank_questions[0].question == f"{tech[0].catalog_ref} hoạt động thế nào?"  # da bo markdown
    finish_turn(r, "Giới thiệu bản thân?", "ai")
    plan, state, question, turn = r.plan, r.state, r.question, r.turn
    seen = []
    for _ in range(8):  # di toi luot ask_main dau tien cua phan technical
        nreq = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=plan, state=state,
                               turn_number=turn.turn_number, question=question, turn_kind=turn.turn_kind,
                               answer="Em trả lời có nội dung kỹ thuật.", elapsed_seconds=60 * turn.turn_number)
        r = run(next_turn(nreq, evaluator=evaluator, retriever=retr))
        if r.session_end:
            break
        q = r.spec.bank_question or "Câu AI tự đặt?"
        finish_turn(r, q, "ai")
        seen.append((r.turn.action, r.turn.qa_id, r.turn.question_source, r.state.current_qa_id))
        state, question, turn = r.state, r.question, r.turn
        if r.turn.qa_id:
            break
    action, qa_id, source, current = seen[-1]
    assert action == "ask_main" and qa_id and source == "bank" and current == qa_id
    assert all(i.reference_answer == "" for i in evaluator.inputs)  # cac cau truoc khong lay tu kho
    nreq = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=plan, state=state,
                           turn_number=turn.turn_number, question=question, turn_kind="main",
                           answer="Em trả lời câu hỏi trong kho.", elapsed_seconds=600)
    run(next_turn(nreq, evaluator=evaluator, retriever=retr))
    assert evaluator.inputs[-1].reference_answer == f"Đáp án chuẩn {qa_id}" and retr.asked == [qa_id]


def test_drifted_rephrase_is_not_graded_with_answer_key():
    bank = "Giải thích các package sau trong Express.js: body-parser, cookie-parser, morgan, cors, dotenv?"
    r = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior"),
                          planner=MockPlanner(), retriever=FakeRetriever()))
    r.state.current_qa_id, r.turn.qa_id, r.spec.bank_question = "x#1", "x#1", bank
    finish_turn(r, "Giờ mình sang Express. Bạn giải thích vai trò của middleware trong Express được không?", "ai")
    assert r.turn.question_source == "ai" and r.turn.qa_id is None and r.state.current_qa_id is None
    r.state.current_qa_id, r.turn.qa_id, r.spec.bank_question = "y#1", "y#1", "Phân biệt JDK, JRE và JVM."
    finish_turn(r, "Mình hỏi một câu cơ bản về Java nhé. Bạn có thể phân biệt JDK, JRE và JVM không?", "ai")
    assert r.turn.question_source == "bank" and r.state.current_qa_id == "y#1"  # them cau dan van giu y


def test_flag_off_keeps_plan_without_bank():
    retr = FakeRetriever()
    retr.question_bank = False
    r = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior"),
                          planner=MockPlanner(), retriever=retr))
    assert not any(t.bank_questions for ph in r.plan.phases for t in ph.topics)


def test_template_fallback_clears_qa_id():
    retr = FakeRetriever()
    r = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior"),
                          planner=MockPlanner(), retriever=retr))
    r.state.current_qa_id, r.turn.qa_id = "x#1", "x#1"
    r.spec.bank_question = "Câu trong kho?"
    finish_turn(r, "Câu mẫu khác hẳn?", "fallback")
    assert r.turn.question_source == "fallback" and r.turn.qa_id is None and r.state.current_qa_id is None


def test_interviewer_and_fallback_use_bank_question():
    tech_topic = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior"),
                                   planner=MockPlanner(), retriever=FakeRetriever())).plan.phases[1].topics[0]
    spec = QuestionSpec("ask_main", "technical", tech_topic, 2, bank_question="HashMap resize khi nào?")
    user = build_messages("SYS", spec)[1]["content"]
    assert '<untrusted label="bank_question">\nHashMap resize khi nào?' in user
    assert fallback_question(spec) == "HashMap resize khi nào?"


def test_evaluator_answer_key_in_prompt_and_completeness_cap():
    topic = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior"),
                              planner=MockPlanner(), retriever=FakeRetriever())).plan.phases[1].topics[0]
    answer = "HashMap dùng mảng bucket, collision thì nối danh sách liên kết và đổi sang cây khi dài"
    inp = EvaluationInput(level="junior", phase="technical", topic=topic, difficulty=2, turn_kind="main",
                          turn_number=3, question="HashMap xử lý collision?", answer=answer,
                          reference_answer="HashMap xử lý collision?\n\nDùng chaining, treeify khi > 8.")
    assert '<untrusted label="reference_answer">\nHashMap xử lý collision?' in eval_messages("SYS", inp)[1]["content"]
    out = EvaluatorOutput(answer_type="answered", covered=[
        {"point": "collision dùng danh sách liên kết", "quote": "collision thì nối danh sách liên kết"},
        {"point": "đổi sang cây khi dài", "quote": "đổi sang cây khi dài"}], missing_points=[], misconceptions=[],
        scores={"technical_accuracy": 4, "completeness": 4, "extensibility": 3, "relevance": 4}, follow_up_focus=None)
    assert postcheck(out, inp).scores.completeness == 3  # 2 y co quote -> tran 3, khong theo key_points ca topic
