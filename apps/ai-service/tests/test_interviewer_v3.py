"""Interviewer v3: tranh mo dau trung (recent_openers), goi y dua tren dap an chuan cua cau dang hoi, chan goi y
chep dap an. LLM gia chi kiem dieu phoi; chat luong van phong do bang evals.sim_style va judge."""
from app.agents.interviewer import QuestionSpec, build_messages, recent_openers
from app.policy import Decision
from app.prompts.store import PromptStore
from app.question_stream import copies_answer, violation
from app.rag.question_bank import kept_meaning
from app.models_interview import NextTurnRequest, StartRequest
from app.agents.planner import MockPlanner
from app.turn_engine import finish_turn, next_turn, start_session
from test_interviewer_stream import SPEC, TOPIC, run_stream
from test_question_bank import CaptureEvaluator, FakeRetriever, run
from fakes.fake_llm import FakeStream

KEY = "HashMap băm key bằng hashCode rồi đặt vào bucket theo chỉ số, va chạm thì nối thành danh sách liên kết"
HINT = QuestionSpec("hint", "technical", TOPIC, 2, focus="xử lý va chạm", last_question="HashMap lưu key thế nào?",
                    reference_answer=KEY)


def test_latest_prompt_is_v3():
    assert PromptStore().get("interviewer").version == "v3"


def test_recent_openers_dedup_last_four():
    avoid = ["gio minh sang phan a", "x", "gio minh sang phan b", "ban co the noi ve c khong", "vay con d"]
    assert recent_openers(avoid) == ["x", "gio minh sang", "ban co the", "vay con d"]
    assert '"recent_openers": ["ban co the"]' in build_messages("SYS", QuestionSpec(
        "ask_main", "technical", TOPIC, 2, avoid=["ban co the giai thich"]))[1]["content"]


def test_reference_answer_only_sent_for_hint():
    assert '<untrusted label="reference_answer">' in build_messages("SYS", HINT)[1]["content"]
    follow = QuestionSpec("follow_up", "technical", TOPIC, 2, focus="x", reference_answer=KEY)
    assert "reference_answer" not in build_messages("SYS", follow)[1]["content"]


def test_hint_copying_answer_key_is_replaced():
    assert copies_answer("Gợi ý: va chạm thì nối thành danh sách liên kết, đúng không?", KEY)
    assert not copies_answer("Thử nghĩ xem hai key cùng hashCode thì nằm ở đâu?", KEY)
    assert violation("Va chạm thì nối thành danh sách liên kết nhé?", [], KEY) == "answer_leak"
    events, qs, _ = run_stream([FakeStream(["Gợi ý: va chạm thì nối thành danh sách liên kết, bạn thử lại?"])],
                               spec=HINT)
    assert events[-1][0] == "replace" and qs.source == "fallback"
    events, qs, _ = run_stream([FakeStream(["Hai key cùng hashCode thì HashMap đặt chúng ở đâu?"])], spec=HINT)
    assert qs.source == "ai"
    assert violation("Vậy proxy xử lý self-invocation ra sao?", [], "") is None and SPEC.reference_answer == ""
    keyed = "HashMap lưu key và value bên trong như thế nào?\n\n" + KEY  # dap an chuan gom ca cau hoi goc
    hint = "Nhớ lại HashMap lưu key và value bên trong như thế nào, thử nghĩ về hashCode?"
    assert copies_answer(hint, keyed) and not copies_answer(hint, keyed, "HashMap lưu key và value bên trong như thế nào?")


def test_engine_passes_answer_key_to_hint(monkeypatch):
    retr, evaluator = FakeRetriever(), CaptureEvaluator()
    req = StartRequest(session_id="s", track="java_backend", level="junior", duration_minutes=20)
    r = run(start_session(req, planner=MockPlanner(), retriever=retr))
    finish_turn(r, "Giới thiệu bản thân?", "ai")
    for _ in range(8):  # toi cau hoi lay tu kho dau tien
        nreq = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=r.plan, state=r.state,
                               turn_number=r.turn.turn_number, question=r.question, turn_kind=r.turn.turn_kind,
                               answer="Em trả lời có nội dung.", elapsed_seconds=60 * r.turn.turn_number)
        r = run(next_turn(nreq, evaluator=evaluator, retriever=retr))
        finish_turn(r, r.spec.bank_question or "Câu AI tự đặt?", "ai")
        if r.turn.qa_id:
            break
    qa_id = r.turn.qa_id
    assert qa_id
    monkeypatch.setattr("app.turn_engine.decide", lambda *a, **k: Decision("hint", 0, "va chạm", "test"))
    nreq = NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=r.plan, state=r.state,
                           turn_number=r.turn.turn_number, question=r.question, turn_kind="main",
                           answer="Em không chắc.", elapsed_seconds=60 * r.turn.turn_number)
    h = run(next_turn(nreq, evaluator=evaluator, retriever=retr))
    assert h.spec.action == "hint" and h.spec.reference_answer == f"Đáp án chuẩn {qa_id}"


def test_short_rephrase_keeps_meaning_but_topic_drift_does_not():
    bank = "Bạn có thể giải thích sự khác biệt giữa int và Integer trong Java không?"
    assert kept_meaning(bank, "int và Integer trong Java khác nhau ở chỗ nào?")  # bo tu khuon van giu nghia
    assert not kept_meaning("Giải thích các package body-parser, cookie-parser, morgan, cors trong Express.js?",
                            "Middleware trong Express hoạt động như thế nào?")


def test_bank_question_hides_opening_hint():
    user = build_messages("SYS", QuestionSpec("ask_main", "technical", TOPIC, 2, bank_question="Proxy là gì?"))[1]
    assert "opening_hint" not in user["content"] and "Spring @Transactional" in user["content"]
    assert "opening_hint" in build_messages("SYS", QuestionSpec("ask_main", "technical", TOPIC, 2))[1]["content"]
