"""Phase 03 (audit H4): o luot co chunk cong cu, chi hieu sai dua HOAN TOAN vao chunk do thoi chan technical_accuracy;
hieu sai khac chan nhu khi tat co. Hieu sai chi dua vao chunk cong cu khong vao Evaluation (Reporter khong thay). Hau kiem thuan, khong LLM."""
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


def test_misconception_resting_only_on_tool_chunk_does_not_cap_and_is_not_reported():
    ev = evaluate(["S2"], [WRONG_POINT + " (sai)"])
    assert ev.scores.technical_accuracy == 3  # S2 la chunk cong cu (base_ids = 1)
    assert ev.misconceptions == []  # M3: Reporter khong bao gio thay no
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


def test_only_capping_misconceptions_are_reported_next_to_a_dropped_tool_one():
    ev = evaluate(["S2"], [WRONG_POINT + " (sai)", "Hiểu sai riêng không gắn nguồn"])
    assert ev.scores.technical_accuracy == 1
    assert ev.misconceptions == ["Hiểu sai riêng không gắn nguồn"]


def test_tool_chunk_cannot_make_scores_higher_than_flag_off_for_supported_point():
    # y chi no_source (id khong hop le bi bo) + misconception tu do: hanh vi nhu tat co
    ev = evaluate(["S9"], [WRONG_POINT + " (sai)"], support="supported")
    assert ev.scores.technical_accuracy == 1


def evaluate_two(misconception, short=False):
    """Hai y contradicted: mot chi dua vao chunk cong cu (S2), mot dua vao snippet co san (S1)."""
    tool = {"point": "HashMap" if short else WRONG_POINT, "quote": WRONG_QUOTE, "source_ids": ["S2"],
            "support": "contradicted"}
    base = {"point": "Index ghi nhanh hơn vì có sẵn chỗ", "quote": "ghi nhanh hơn vì có sẵn chỗ",
            "source_ids": ["S1"], "support": "contradicted"}
    out = EvaluatorOutputV4.model_validate({
        "answer_type": "answered", "covered": [GOOD, tool, base], "missing_points": [],
        "misconceptions": [misconception], "follow_up_focus": None,
        "scores": {"technical_accuracy": 3, "completeness": 3, "extensibility": 2, "relevance": 3}})
    return postcheck(out, inp(1))


def test_short_point_does_not_free_an_unrelated_misconception_by_containment():
    ev = evaluate_two("Nhầm HashMap là thread-safe (theo kiến thức riêng)", short=True)  # "HashMap" chi 1 tu
    assert ev.scores.technical_accuracy == 1 and ev.misconceptions


def test_misconception_matching_both_tool_and_base_point_still_caps():
    ev = evaluate_two("Index làm ghi nhanh hơn, tức là Index ghi nhanh hơn vì có sẵn chỗ")
    assert ev.scores.technical_accuracy == 1
    ev2 = evaluate_two(WRONG_POINT + " (sai)")  # chi khop y cong cu: van duoc bo
    assert ev2.scores.technical_accuracy == 3 and ev2.misconceptions == []
