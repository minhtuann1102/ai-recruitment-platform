"""Builder request tu checkpoint (phase 04): request noi bo dung lai phai BANG request cu ben goi tu dung tay.

So tung luot cua cac kich ban golden phase 01 (text, voice reask, hybrid + swap, cau trong kho, qua han cung...) voi
request ben goi gia (tests/golden_turns) dang gui; finalize so voi danh sach turns ben goi gia ghi trong trace.
"""
import pytest

from app.api_error import ApiError
from app.models_interview import FinalizeTurn, NextTurnRequest
from app.models_interview_http import FinalizeBody, NextTurnBody
from app.session_store.session_request_builder import build_finalize_request, build_next_turn_request
from tests.golden_turns import golden_scenarios
from tests.golden_turns.golden_scenarios import SCENARIOS, run_scenario
from tests.helpers.seed_session import seed_session
from tests.session_store_helpers import stored

TURN_KEYS = ("answer", "answer_source", "stt_confidence")


def comparing_run_session(real, checked):
    """run_session cua golden, moi luot so request dung lai tu checkpoint voi request ben goi gia sap gui."""
    def wrapped(client, sid, track, level, answer_for, **kw):
        def compare(step, caller, topic):
            fields = answer_for(step, caller, topic)
            if fields is not None and not caller.ended:
                slim = {"session_id": sid, "turn_number": caller.turn_number, "elapsed_seconds": caller.turn_number * 60,
                        **fields}
                built = build_next_turn_request(NextTurnBody(**slim), stored(sid))
                want = NextTurnRequest(level=level, track=track, plan=caller.plan, state=caller.state,
                                       question=caller.question, turn_kind=caller.turn["turn_kind"],
                                       topic_turns=caller.topic_turns, **slim)
                assert built.model_dump() == want.model_dump(), f"{sid} luot {caller.turn_number}"
                checked.append(sid)
            return fields
        trace = real(client, sid, track, level, compare, **kw)
        if "finalize" in trace:
            sent = trace["finalize"]["request"]
            built = build_finalize_request(FinalizeBody(session_id=sid, end_reason=sent["end_reason"],
                                                        duration_s=sent["duration_s"]), stored(sid))
            assert [t.model_dump() for t in built.turns] == [FinalizeTurn(**t).model_dump() for t in sent["turns"]]
            assert built.state.end_reason == sent["end_reason"] and built.jd_profile is None
            checked.append(sid + ":finalize")
        return trace
    return wrapped


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_rebuilt_requests_equal_hand_built_ones_on_every_golden_turn(name, monkeypatch):
    checked = []
    monkeypatch.setattr(golden_scenarios, "run_session", comparing_run_session(golden_scenarios.run_session, checked))
    run_scenario(name)
    assert len(checked) >= 2


# --- Truong hop rieng (checkpoint dung tay) ---
def entry(n, topic, q="q", a="a", source="text"):
    return {"turn_number": n, "question": f"{q}{n}", "answer": f"{a}{n}", "source": source, "topic_id": topic,
            "phase": "technical", "turn_kind": "main", "difficulty": None, "evaluation": None}


def plan_state(client, sid="b1"):
    from conftest import parse_sse
    d = parse_sse(client.post("/api/start", json={"session_id": sid, "track": "java_backend",
                                                  "level": "junior"}).text)[-1][1]
    return d


def test_topic_turns_are_the_last_five_of_the_asked_topic_only(client):
    d = plan_state(client)
    transcript = [entry(1, "t1"), entry(2, "t2", source="voice")] + [entry(n, "t2") for n in range(3, 9)]
    seed_session(client, "b1", d["plan"], d["state"], transcript, {**d["turn"], "topic_id": "t2", "turn_kind": "hint"},
                 "cau hien tai")
    req = build_next_turn_request(NextTurnBody(session_id="b1", turn_number=1, answer="x", stt_confidence=0.5),
                                  stored("b1"))
    assert [t.q for t in req.topic_turns] == [f"q{n}" for n in range(4, 9)] and req.turn_kind == "hint"
    assert req.question == "cau hien tai" and req.stt_confidence == 0.5 and req.track == "java_backend"


def test_finalize_without_transcript_is_409_and_keeps_stored_end_reason(client):
    d = plan_state(client)
    with pytest.raises(ApiError) as err:
        build_finalize_request(FinalizeBody(session_id="b1", end_reason="candidate_ended", duration_s=5), stored("b1"))
    assert err.value.status_code == 409 and err.value.error == "session_no_turns"
    seed_session(client, "b1", d["plan"], d["state"], [entry(1, "t1")], d["turn"], "q")
    req = build_finalize_request(FinalizeBody(session_id="b1", end_reason="candidate_ended", duration_s=5), stored("b1"))
    assert req.state.end_reason == "candidate_ended" and req.state.phase == "done" and req.turns[0].difficulty == 2  # difficulty None -> mac dinh 2
    done = {**d["state"], "phase": "done", "end_reason": "plan_complete"}
    seed_session(client, "b1", d["plan"], done, [entry(1, "t1")], d["turn"], "q")
    req = build_finalize_request(FinalizeBody(session_id="b1", end_reason="candidate_ended", duration_s=5), stored("b1"))
    assert req.state.end_reason == "plan_complete" and req.end_reason == "plan_complete"  # mot nguon: state da luu thang


def test_http_bodies_forbid_old_fields():
    with pytest.raises(ValueError):
        NextTurnBody(session_id="s", turn_number=1, answer="x", plan={})
    with pytest.raises(ValueError):
        FinalizeBody(session_id="s", end_reason="x", duration_s=1, turns=[])
    with pytest.raises(ValueError):
        NextTurnBody(session_id="s", turn_number=1, answer="")  # go tay khong duoc rong
    assert NextTurnBody(session_id="s", turn_number=1, answer="", answer_source="voice").answer == ""
