"""Phase 03a: Evaluator v4 trich nguon (S1.., R); code kiem id, contradicted -> misconception, confidence.
LLM gia, khong do chat luong cham."""
import app.agents.evaluator_provider as provider
from app.agents.evaluator import (EvaluationInput, EvaluatorOutput, EvaluatorOutputV4, build_messages, postcheck,
                                  uses_sources)
from app.evaluator_source_checks import SourcedPoint, check_sources, confidence, merge_misconceptions, source_blocks
from app.models_interview import PlanTopic

KP = ["Index B-tree giúp tìm nhanh thay vì quét toàn bảng", "Index làm chậm thao tác ghi",
      "Composite index theo leftmost prefix"]
ANSWER = "DB dùng B-tree nên không phải quét cả bảng. Index làm ghi nhanh hơn vì có sẵn chỗ."


def topic(snippets=("Index B-tree ... (tài liệu)",)):
    return PlanTopic(id="t1", title="Index", source="catalog", objective="o", key_points=KP, start_difficulty=2,
                     opening_hint="h", backup_question="b", reference_snippets=list(snippets))


def inp(snippets=("Index B-tree ... (tài liệu)",), turn=(), ref=""):
    return EvaluationInput(level="junior", phase="technical", topic=topic(snippets), difficulty=2, turn_kind="main",
                           turn_number=2, question="Index?", answer=ANSWER, reference_answer=ref,
                           turn_snippets=list(turn))


def out(*covered, cls=EvaluatorOutputV4, misconceptions=()):
    return cls.model_validate({
        "answer_type": "answered", "covered": list(covered), "missing_points": [],
        "misconceptions": list(misconceptions), "follow_up_focus": None,
        "scores": {"technical_accuracy": 3, "completeness": 3, "extensibility": 2, "relevance": 3}})


GOOD = {"point": KP[0], "quote": "DB dùng B-tree nên không phải quét cả bảng", "source_ids": ["S1"],
        "support": "supported"}
WRONG = {"point": "Index làm ghi nhanh hơn", "quote": "Index làm ghi nhanh hơn vì có sẵn chỗ",
         "source_ids": ["s2"], "support": "contradicted"}


def test_ids_follow_prompt_order_topic_then_turn_then_reference():
    assert [i for i, _ in source_blocks(["a", "b"], "ref")] == ["S1", "S2", "R"]
    user = build_messages("SYS", inp(turn=["chunk lượt"], ref="đáp án"), with_ids=True)[1]["content"]
    assert "[S1] Index B-tree" in user and "[S2] chunk lượt" in user and "[R] đáp án" in user
    plain = build_messages("SYS", inp(turn=["chunk lượt"], ref="đáp án"))[1]["content"]
    assert "[S1]" not in plain and "đáp án" in plain  # v3: khong danh id


def test_unknown_ids_dropped_and_supported_without_valid_id_becomes_no_source():
    kept, refuted, invalid = check_sources([SourcedPoint("p", "q", ["S9", "R"], "supported")], ["S1"])
    assert refuted == [] and invalid == 2 and kept[0].support == "no_source" and kept[0].source_ids == []


def test_reference_answer_contradiction_becomes_misconception_and_caps_accuracy():
    ev = postcheck(out(GOOD, {**WRONG, "source_ids": ["R"]}), inp(ref="Index làm chậm thao tác ghi"))
    assert ev.covered_points == [KP[0]] and ev.misconceptions == ["Index làm ghi nhanh hơn"]
    assert ev.scores.technical_accuracy == 1  # luat 4
    assert ev.evidence[0].source_ids == ["S1"] and ev.evidence[0].support == "supported"
    assert ev.confidence == "high"


def test_snippet_contradiction_is_not_credited_but_does_not_cap():
    # chunk BM25 chi gan dung chu de: khong tinh covered, nhung khong du de chan technical_accuracy
    ev = postcheck(out(GOOD, WRONG), inp(turn=["Index làm chậm thao tác ghi"]))
    assert ev.covered_points == [KP[0]] and ev.misconceptions == [] and ev.scores.technical_accuracy == 3


def test_misconceptions_put_code_checked_first_and_drop_near_duplicates():
    merged = merge_misconceptions(["Index làm ghi nhanh hơn"],
                                  ["Cho rằng index làm ghi nhanh hơn", "Cho rằng B-tree là hash", "Nghĩ index không tốn bộ nhớ"])
    assert merged == ["Index làm ghi nhanh hơn", "Cho rằng B-tree là hash", "Nghĩ index không tốn bộ nhớ"]
    ev = postcheck(out({**WRONG, "source_ids": ["R"]}, misconceptions=["Cho rằng B-tree là hash", "Nghĩ index không tốn bộ nhớ"]), inp(ref="đáp án"))
    assert ev.misconceptions[0] == "Index làm ghi nhanh hơn"  # khong bi cat khi chi giu 2


def test_reference_only_turn_uses_r_and_rates_confidence():
    ev = postcheck(out({**GOOD, "source_ids": ["R"]}), inp(snippets=(), ref="đáp án"))
    assert ev.evidence[0].source_ids == ["R"] and ev.confidence == "high"


def test_version_parsing_and_bad_prompt_version_degrades_instead_of_500(monkeypatch):
    assert [uses_sources(v) for v in ("v1", "v2", "v3", "v4", "v10")] == [False, False, False, True, True]
    monkeypatch.setenv("AGENT_EVALUATOR_MODE", "llm")
    monkeypatch.setenv("EVALUATOR_PROMPT_VERSION", "v9")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setattr(provider, "_llm", None)
    assert isinstance(provider.get_evaluator(), provider.MockEvaluator)


def test_contradicted_without_valid_id_stays_covered_as_no_source():
    ev = postcheck(out({**WRONG, "source_ids": ["S7"]}), inp())
    assert ev.misconceptions == [] and ev.evidence[0].support == "no_source"


def test_confidence_low_when_sources_exist_but_nothing_supported_and_none_without_sources():
    unsupported = {**GOOD, "source_ids": [], "support": "no_source"}
    assert postcheck(out(unsupported), inp()).confidence == "low"
    no_docs = postcheck(out(GOOD), inp(snippets=()))
    assert no_docs.confidence is None and no_docs.evidence[0].support == "no_source"  # khong tai lieu: S1 la id la
    assert confidence([], True) is None


def test_v3_output_keeps_old_behaviour():
    v3 = {k: GOOD[k] for k in ("point", "quote")}
    ev = postcheck(out(v3, cls=EvaluatorOutput), inp())
    assert ev.confidence is None and ev.evidence[0].support is None and ev.evidence[0].source_ids == []
