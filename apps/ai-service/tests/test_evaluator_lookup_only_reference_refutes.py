"""Phase 03 (audit H4): o luot co chunk cong cu, chi hieu sai dua HOAN TOAN vao chunk do thoi chan technical_accuracy;
hieu sai khac chan nhu khi tat co. Hau kiem thuan, khong LLM."""
import pytest

from app.agents.evaluator import EvaluationInput, EvaluatorOutputV4, postcheck
from app.models_interview import PlanTopic, SourceRef

KP = ["Index B-tree giúp tìm nhanh thay vì quét toàn bảng", "Index làm chậm thao tác ghi",
      "Composite index theo leftmost prefix"]
ANSWER = "DB dùng B-tree nên không phải quét cả bảng. Index làm ghi nhanh hơn vì có sẵn chỗ."
WRONG_POINT = "Index làm ghi nhanh hơn"
WRONG_QUOTE = "Index làm ghi nhanh hơn vì có sẵn chỗ"
GOOD = {"point": KP[0], "quote": "DB dùng B-tree nên không phải quét cả bảng", "source_ids": ["S1"],
        "support": "supported"}


def inp(tool_base_ids):
    topic = PlanTopic(id="t1", title="Index", source="catalog", objective="o", key_points=KP, start_difficulty=2,
                      opening_hint="h", backup_question="b", reference_snippets=["Index B-tree (tài liệu có sẵn)"],
                      reference_sources=[SourceRef(ref="topic-doc", title="Doc")])
    return EvaluationInput(level="junior", phase="technical", topic=topic, difficulty=2, turn_kind="main",
                           turn_number=2, question="Index?", answer=ANSWER,
                           turn_snippets=["Chunk tra cứu: ghi chậm hơn"],
                           turn_sources=[SourceRef(ref="tool-doc", title="Tool")], tool_base_ids=tool_base_ids)


def evaluate(ids, misconceptions, tool_base_ids=1, support="contradicted"):
    wrong = {"point": WRONG_POINT, "quote": WRONG_QUOTE, "source_ids": ids, "support": support}
    out = EvaluatorOutputV4.model_validate({
        "answer_type": "answered", "covered": [GOOD, wrong], "missing_points": [], "misconceptions": misconceptions,
        "follow_up_focus": None, "scores": {"technical_accuracy": 3, "completeness": 3, "extensibility": 2,
                                            "relevance": 3}})
    return postcheck(out, inp(tool_base_ids))


def test_misconception_resting_only_on_tool_chunk_does_not_cap_but_is_reported():
    ev = evaluate(["S2"], [WRONG_POINT + " (sai)"])
    assert ev.scores.technical_accuracy == 3  # S2 la chunk cong cu (base_ids = 1)
    assert ev.misconceptions == [WRONG_POINT + " (sai)"]  # van vao bao cao
    assert {s.id: s.support for s in ev.sources} == {"S1": "supported", "S2": "contradicted"} and WRONG_POINT not in ev.covered_points


def test_same_output_with_flag_off_caps_technical_accuracy():
    assert evaluate(["S2"], [WRONG_POINT + " (sai)"], tool_base_ids=None).scores.technical_accuracy == 1


@pytest.mark.parametrize("ids", [["S1"], ["S1", "S2"]])
def test_contradiction_from_existing_snippet_or_mixed_ids_still_caps(ids):
    ev = evaluate(ids, [WRONG_POINT + " (sai)"])
    assert ev.scores.technical_accuracy == 1 and ev.misconceptions == [WRONG_POINT + " (sai)"]


def test_unsourced_misconception_still_caps_even_when_tool_chunk_exists():
    ev = evaluate(["S2"], ["Khẳng định khác hoàn toàn không liên quan nguồn nào"])
    assert ev.scores.technical_accuracy == 1


def test_blocking_misconception_is_listed_before_uncapped_one_and_still_caps():
    ev = evaluate(["S2"], [WRONG_POINT + " (sai)", "Hiểu sai riêng không gắn nguồn"])
    assert ev.scores.technical_accuracy == 1
    assert ev.misconceptions == ["Hiểu sai riêng không gắn nguồn", WRONG_POINT + " (sai)"]


def test_tool_chunk_cannot_make_scores_higher_than_flag_off_for_supported_point():
    # y chi no_source (id khong hop le bi bo) + misconception tu do: hanh vi nhu tat co
    ev = evaluate(["S9"], [WRONG_POINT + " (sai)"], support="supported")
    assert ev.scores.technical_accuracy == 1
