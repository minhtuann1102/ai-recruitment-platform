"""Luot voice (NFR-AI-QUAL17): doi thuat ngu cho moi noi doc cau tra loi, ban ghi STT kem thi hoi lai / khong cham,
goi y thuat ngu cho dich vu STT. Khong goi LLM."""
import asyncio

from fastapi.testclient import TestClient

from app.agents.planner import MockPlanner
from app.api_error import ApiError
from app.main import app
from app.mock_evaluator import is_scored
from app.models_interview import NextTurnRequest, StartRequest, TopicTurn
from app.question_stream import QuestionStream
from app.stt_phrase_hints import _VI_WORDS, latin_phrases, track_phrases
from app.stt_terms import STT_TERMS
from app.turn_engine import finish_turn, next_turn, start_session
from app.voice_turn import REASK, STT_MIN_CONFIDENCE
from test_question_bank import CaptureEvaluator, FakeRetriever

SPOKEN = "Em dùng con ca rừn hát mắp để nhiều thờ rét cùng ghi an toàn"
LOW = STT_MIN_CONFIDENCE - 0.1


def run(coro):
    return asyncio.run(coro)


def session():
    """Toi luot ask_main dau tien co cau trong kho (qa_id) de kiem hoi lai giu dap an chuan."""
    retr, evaluator = FakeRetriever(), CaptureEvaluator()
    r = run(start_session(StartRequest(session_id="s", track="java_backend", level="junior", duration_minutes=20),
                          planner=MockPlanner(), retriever=retr))
    finish_turn(r, "Giới thiệu bản thân?", "ai")
    for _ in range(8):
        if r.turn.qa_id:
            return r
        r = run(next_turn(req(r, "Em trả lời có nội dung kỹ thuật."), evaluator=evaluator, retriever=retr))
        finish_turn(r, r.spec.bank_question or "Câu AI tự đặt?", "ai")
    raise AssertionError("khong toi duoc cau trong kho")


def req(r, answer, **over):
    return NextTurnRequest(session_id="s", level="junior", track="java_backend", plan=r.plan, state=r.state,
                           turn_number=r.turn.turn_number, question=r.question, turn_kind=r.turn.turn_kind,
                           answer=answer, elapsed_seconds=60 * r.turn.turn_number, **over)


def stream_text(spec):
    qs = QuestionStream(spec, interviewer=None, asked=[])  # interviewer None: goi LLM thi test vo

    async def collect():
        return "".join([d["t"] async for kind, d in qs.events() if kind == "token"])
    return run(collect()), qs.source


def test_voice_answer_is_normalized_for_evaluator_rag_and_interviewer():
    r, evaluator = session(), CaptureEvaluator()
    out = run(next_turn(req(r, SPOKEN, answer_source="voice", stt_confidence=0.95,
                            topic_turns=[TopicTurn(q="Q trước", a="em dùng hát mắp"),
                                         TopicTurn(q="Q gõ", a="nem gia va hát mắp", source="text")]),
                        evaluator=evaluator, retriever=FakeRetriever()))
    inp = evaluator.inputs[-1]
    assert inp.spoken and inp.answer == SPOKEN  # Evaluator tu doi, con giu ban ghi goc de trich quote
    assert inp.topic_turns[0].a == "em dùng HashMap"  # khong ghi nguon: cung nguon voi luot hien tai
    assert inp.topic_turns[1].a == "nem gia va hát mắp"  # luot go tay giu nguyen
    assert "ConcurrentHashMap" in out.spec.last_answer and "thread" in out.spec.last_answer


def test_typed_answer_and_missing_confidence_change_nothing():
    r, evaluator = session(), CaptureEvaluator()
    out = run(next_turn(req(r, SPOKEN, stt_confidence=0.1), evaluator=evaluator, retriever=FakeRetriever()))
    assert not evaluator.inputs[-1].spoken and out.spec.last_answer == SPOKEN  # text: confidence bi bo qua
    assert not out.evaluation.transcript_low_confidence
    run(next_turn(req(r, SPOKEN, answer_source="voice"), evaluator=evaluator, retriever=FakeRetriever()))
    assert evaluator.inputs[-1].spoken  # voice khong co confidence: van cham


def test_low_confidence_reasks_same_question_once_without_scoring():
    r, evaluator = session(), CaptureEvaluator()
    qa_id, difficulty, n_scored = r.state.current_qa_id, r.state.current_difficulty, r.state.evaluated_turns
    out = run(next_turn(req(r, SPOKEN, answer_source="voice", stt_confidence=LOW), evaluator=evaluator,
                        retriever=FakeRetriever()))
    assert evaluator.inputs == []  # khong goi Evaluator
    assert out.evaluation.transcript_low_confidence and not is_scored(out.evaluation)
    assert (out.turn.action, out.turn.turn_kind, out.turn.topic_id) == ("clarify", r.turn.turn_kind, r.turn.topic_id)
    assert out.state.current_qa_id == qa_id and out.state.current_difficulty == difficulty
    assert out.state.evaluated_turns == n_scored and out.state.counters.stt_reasks == 1
    assert out.state.counters.follow_ups == r.state.counters.follow_ups  # khong ton luot hoi sau
    text, source = stream_text(out.spec)
    assert text == REASK.format(q=r.question) and source == "fallback"
    finish_turn(out, text, source)
    assert out.turn.qa_id == qa_id and out.turn.question_source == "bank"  # dap an chuan van dung cho luot sau


def test_reasked_hint_keeps_hint_kind_for_band_cap():
    r = session()
    hint = req(r, SPOKEN, answer_source="voice", stt_confidence=LOW).model_copy(update={"turn_kind": "hint"})
    out = run(next_turn(hint, evaluator=CaptureEvaluator(), retriever=FakeRetriever()))
    assert (out.turn.action, out.turn.turn_kind) == ("clarify", "hint")  # luot sau van bi tran band cua hint


def test_second_low_confidence_in_topic_suggests_chat_and_keeps_state():
    r = session()
    first = run(next_turn(req(r, SPOKEN, answer_source="voice", stt_confidence=LOW), evaluator=CaptureEvaluator(),
                          retriever=FakeRetriever()))
    finish_turn(first, first.spec.fixed_question, "fallback")
    evaluator, again = CaptureEvaluator(), req(first, SPOKEN, answer_source="voice", stt_confidence=LOW)
    try:
        run(next_turn(again, evaluator=evaluator, retriever=FakeRetriever()))
    except ApiError as err:
        assert err.error == "voice_unclear" and err.details == {"retryable": True, "suggest_chat": True}
    else:
        raise AssertionError("khong bao voice_unclear")
    assert evaluator.inputs == []
    typed = run(next_turn(again.model_copy(update={"answer_source": "text", "stt_confidence": None}),
                          evaluator=evaluator, retriever=FakeRetriever()))  # go chat, gui lai cung luot: cham
    assert len(evaluator.inputs) == 1 and not typed.evaluation.transcript_low_confidence


def test_low_confidence_does_not_reask_when_time_is_up():
    r = session()
    late = req(r, SPOKEN, answer_source="voice", stt_confidence=LOW).model_copy(update={"elapsed_seconds": 20 * 60})
    out = run(next_turn(late, evaluator=CaptureEvaluator(), retriever=FakeRetriever()))
    assert out.turn.action == "wrap_up" and out.evaluation.transcript_low_confidence


def test_phrase_hints_come_from_catalog_then_common_terms():
    phrases = track_phrases("java_backend")
    assert {"ConcurrentHashMap", "thread pool", "ExecutorService", "Spring Boot auto-configuration"} <= set(phrases)
    assert phrases.index("ConcurrentHashMap") < phrases.index("Kubernetes")  # thuat ngu track truoc
    assert set(STT_TERMS) <= set(phrases) and len(set(phrases)) == len(phrases)
    assert not {w.lower() for p in phrases for w in p.split()} & _VI_WORDS
    assert latin_phrases("thread pool và ExecutorService, tra cứu bằng index") == ["thread pool", "ExecutorService",
                                                                                    "index"]
    assert latin_phrases("OWASP Top 10 cho LLM, 10 lỗi") == ["OWASP Top 10", "LLM"]


def test_phrase_hints_endpoint():
    client = TestClient(app)
    body = client.get("/api/stt/phrases", params={"track": "java_backend"}).json()
    assert body["track"] == "java_backend" and "HashMap" in body["phrases"]
    for bad in ("khong-co", "../../../../pnpm-workspace", "java_backend/../java_backend"):
        assert client.get("/api/stt/phrases", params={"track": bad}).status_code == 422  # khong doc file ngoai catalog


def test_silent_voice_answer_returns_no_speech_without_scoring():
    r, evaluator = session(), CaptureEvaluator()
    for silent in ("", "   ", "ừm... à", "Ờ, ừ hm"):
        try:
            run(next_turn(req(r, silent, answer_source="voice"), evaluator=evaluator, retriever=FakeRetriever()))
        except ApiError as err:
            assert err.error == "voice_no_speech" and err.details == {"retryable": True, "suggest_chat": True}
        else:
            raise AssertionError(f"khong bao voice_no_speech: {silent!r}")
    assert evaluator.inputs == []
    run(next_turn(req(r, "ừm em dùng đốc cơ", answer_source="voice"), evaluator=evaluator, retriever=FakeRetriever()))
    assert len(evaluator.inputs) == 1  # co noi dung: cham binh thuong


def test_no_speech_and_empty_text_over_http():
    client, r = TestClient(app), session()
    body = req(r, "", answer_source="voice").model_dump()
    out = client.post("/api/next-turn", json=body)
    assert out.status_code == 422 and out.json()["error"] == "voice_no_speech"
    out = client.post("/api/next-turn", json={**body, "answer_source": "text"})
    assert out.status_code == 422 and out.json()["error"] == "invalid_request"  # cau go tay rong van bi chan nhu cu


def test_silent_or_unclear_answer_yields_to_time_up_and_wrap_up():
    r = session()
    for over in ({"answer": ""}, {"answer": SPOKEN, "stt_confidence": LOW}):
        late = req(r, SPOKEN, answer_source="voice").model_copy(update={"elapsed_seconds": 20 * 60, **over})
        out = run(next_turn(late, evaluator=CaptureEvaluator(), retriever=FakeRetriever()))
        assert out.turn.action == "wrap_up" and out.evaluation.transcript_low_confidence  # khong chan ca phien
    wrap = req(r, "", answer_source="voice")
    wrap.state.phase = "wrap_up"
    assert run(next_turn(wrap, evaluator=CaptureEvaluator(), retriever=FakeRetriever())).session_end
