"""Chong lap cau hoi (FR-AI-038): policy chon focus chua hoi, cau du phong ne cau da hoi (ca che do LLM)."""
import asyncio

from app.agents.interviewer import QuestionSpec, fallback_question
from app.focus import deepen_focus, gap_focus, pick
from app.models_interview import CandidateState, Evaluation, PlanTopic
from app.policy import decide
from app.question_stream import QuestionStream, is_repeat
from evals.personas import all_personas
from evals.simulate import run_all, summarize
from evals.cost_latency import load_pricing
from evals.simulator import RuleSimulator
from fakes.fake_llm import FakeOpenAI, FakeStream

TOPIC = PlanTopic(id="t2", title="Spring @Transactional", source="catalog", objective="o",
                  key_points=["Nêu được propagation", "Nêu được rollback rules", "Nêu được self-invocation"],
                  start_difficulty=2, opening_hint="h", backup_question="@Transactional hoạt động thế nào?")


def ev(score: int, covered=(), missing=()):
    return Evaluation(turn_number=2, answer_type="answered", covered_points=list(covered),
                      missing_points=list(missing), scores={k: score for k in
                      ("technical_accuracy", "completeness", "extensibility", "relevance")},
                      scores_10={k: score * 2.5 for k in ("technical_accuracy", "completeness", "extensibility",
                                                          "relevance")}, turn_score_10=score * 2.5)


def test_pick_skips_used_and_duplicates():
    assert pick(["Nêu được A B C", "a b c", "D"], ["x"]) == "A B C"
    assert pick(["A B C", "D"], ["a b c"]) == "D" and pick([None, ""], []) is None


def test_strong_answers_get_different_focus_each_follow_up():
    strong = ev(4, covered=["propagation", "rollback rules", "self-invocation"])
    used = []
    for _ in range(3):
        f = deepen_focus(strong, TOPIC, used)
        assert f and "Spring @Transactional" in f and f not in used
        used.append(f)
    first_uncovered = deepen_focus(ev(4, covered=["propagation"]), TOPIC, [])
    assert first_uncovered == "rollback rules"


def test_policy_moves_on_when_every_gap_was_asked():
    ok = ev(2, covered=["propagation"], missing=["rollback rules"])
    state = CandidateState()
    assert decide(ok, state, "junior", False, TOPIC).focus == "rollback rules"
    dec = decide(ok, state, "junior", False, TOPIC, ["rollback rules"])
    assert dec.action == "follow_up" and dec.focus == "self-invocation"  # y chua neu tiep theo
    assert gap_focus(ok, TOPIC, ["rollback rules", "self-invocation"]) is None
    assert decide(ok, state, "junior", False, TOPIC, ["rollback rules", "self-invocation"]).action == "next_topic"


def test_fallback_question_avoids_asked_variants():
    spec = QuestionSpec("follow_up", "technical", TOPIC, 2, focus="rollback rules")
    first = fallback_question(spec)
    spec.avoid = [first]
    second = fallback_question(spec)
    assert second != first and not is_repeat(second, [first])
    spec.avoid = [first, second]
    third = fallback_question(spec)
    assert third not in (first, second)
    spec.avoid = [first, second, third]
    assert fallback_question(spec) == first  # moi cach deu lap: van tra cau dau


def test_llm_repeat_replaced_by_non_repeating_variant():
    from app.agents.interviewer import LlmInterviewer
    from app.llm.gateway import LlmGateway
    from app.llm.settings import load_llm_settings

    spec = QuestionSpec("follow_up", "technical", TOPIC, 2, focus="rollback rules")
    repeated = fallback_question(spec)
    spec.avoid = [repeated]
    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), FakeOpenAI([FakeStream([repeated])]), env={})
    qs = QuestionStream(spec, LlmInterviewer(gw), [repeated])

    async def run():
        return [e async for e in qs.events()]

    events = asyncio.run(run())
    assert events[-1][0] == "replace" and not is_repeat(events[-1][1]["question"], [repeated])


def test_harness_repeat_rate_below_five_percent():
    ids = ["junior-java-strong", "junior-java-average", "junior-java-weak", "middle-nodejs-strong"]
    sessions = asyncio.run(run_all(ids, RuleSimulator()))
    assert summarize(sessions, all_personas(), load_pricing())["constraints"]["repeat_rate"] < 0.05


def test_points_covered_in_earlier_turns_are_not_asked_again():
    turn2 = ev(4, covered=["self-invocation"])
    focus = deepen_focus(turn2, TOPIC, ["self-invocation"], covered=["propagation", "rollback rules"])
    assert focus and "Spring @Transactional" in focus  # khong quay lai propagation da tra loi o luot 1


def test_loose_coverage_matches_paraphrased_points():
    paraphrased = ev(4, covered=["propagation REQUIRES_NEW", "rollback rule cho checked exception",
                                 "self invocation qua proxy"])
    assert "Spring @Transactional" in deepen_focus(paraphrased, TOPIC, [])


def test_state_keeps_topic_coverage_and_only_safe_focus(client):
    from conftest import parse_sse

    done = parse_sse(client.post("/api/start", json={"session_id": "s", "track": "java_backend",
                                                     "level": "junior"}).text)[-1][1]
    topic = done["plan"]["phases"][0]["topics"][0]
    body = {"session_id": "s", "level": "junior", "track": "java_backend", "plan": done["plan"],
            "state": done["state"], "turn_number": 1, "question": done["question"], "elapsed_seconds": 60,
            "answer": ". ".join(topic["key_points"]) + ". chi tiết " * 10}
    nd = parse_sse(client.post("/api/next-turn", json=body).text)[-1][1]
    ts = next(t for t in nd["state"]["topics"] if t["id"] == topic["id"])
    assert ts["covered"] and all("ignore" not in f.lower() for f in ts["focus_used"])
