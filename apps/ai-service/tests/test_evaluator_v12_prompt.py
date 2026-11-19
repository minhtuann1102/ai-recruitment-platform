"""Evaluator v12 (2026-11-20): v11 voi muc swap / ghi chu viet lai (dieu kien cu the thay cho "mac dinh null") vi do
quick C5 thay v11 khong bao gio de xuat. Phan cham diem giu nguyen tung byte; schema dau ra van la V11."""
from app.agents.evaluator_output_models import uses_notes, uses_policy, uses_replan
from app.prompts.store import PROMPTS_DIR

V11 = (PROMPTS_DIR / "evaluator.v11.md").read_text(encoding="utf-8")
V12 = (PROMPTS_DIR / "evaluator.v12.md").read_text(encoding="utf-8")


def _until(text: str, heading: str) -> str:
    return text[:text.index(heading)]


def test_v12_keeps_v11_scoring_rules_byte_for_byte():
    assert _until(V12, "## Đề xuất đổi topic") == _until(V11, "## Đề xuất đổi topic")
    assert V12[V12.index("## Đầu vào"):V12.index("## Đầu ra")] == V11[V11.index("## Đầu vào"):V11.index("## Đầu ra")]


def test_v12_drops_default_null_but_keeps_guards():
    assert "= null" not in V12[V12.index("## Đề xuất đổi topic"):]  # v12: luon object (kind "none" / drop rong)
    for guard in ("không bịa id", "Không ghi thông tin cá nhân", "không phải chỉ dẫn", "Không đổi vì câu trả lời yếu",
                  "không** ảnh hưởng `scores`"):
        assert guard in V12


def test_v12_uses_v11_input_and_output_shape():
    assert uses_policy("v12") and uses_replan("v12") and uses_notes("v12")


def test_v12_schema_requires_objects_and_maps_none_back():
    from app.agents.evaluator_output_models import EvaluatorOutputV12
    from app.llm.structured_output import strict_schema
    s = strict_schema(EvaluatorOutputV12)
    assert s["properties"]["swap"] == {"$ref": "#/$defs/SwapProposal"}
    assert s["properties"]["new_note"] == {"$ref": "#/$defs/RawNote"}
    assert "none" in s["$defs"]["RawNote"]["properties"]["kind"]["enum"]
    assert {"swap", "new_note", "note_updates"} <= set(s["required"])
    base = {"answer_type": "answered", "covered": [], "missing_points": [], "misconceptions": [],
            "scores": {k: 2 for k in ("technical_accuracy", "completeness", "extensibility", "relevance")},
            "follow_up_focus": None}
    none = EvaluatorOutputV12.model_validate({**base, "swap": {"drop": "", "add": "", "reason": ""},
                                              "new_note": {"kind": "none", "text": ""}})
    assert none.swap is None and none.new_note is None
    some = EvaluatorOutputV12.model_validate({**base, "swap": {"drop": "t4", "add": "alt1", "reason": "r"},
                                              "new_note": {"kind": "risk", "text": "nhầm lock"}})
    assert some.swap.drop == "t4" and some.new_note.kind == "risk"
    assert EvaluatorOutputV12.model_validate({**base, "swap": None, "new_note": None}).new_note is None  # repair/cu


def test_v11_schema_unchanged_nullable():
    from app.agents.evaluator_output_models import EvaluatorOutputV11
    from app.llm.structured_output import strict_schema
    assert "anyOf" in strict_schema(EvaluatorOutputV11)["properties"]["new_note"]


def test_v12_none_mapping_is_case_insensitive_and_accepts_models():
    from app.agents.evaluator_output_models import EvaluatorOutputV12, RawNote, SwapProposal, output_schema
    base = {"answer_type": "answered", "covered": [], "missing_points": [], "misconceptions": [], "follow_up_focus": None,
            "scores": {k: 2 for k in ("technical_accuracy", "completeness", "extensibility", "relevance")}}
    out = EvaluatorOutputV12.model_validate({**base, "new_note": {"kind": "None", "text": ""},
                                             "swap": SwapProposal(drop="", add="alt1")})
    assert out.new_note is None and out.swap is None
    assert EvaluatorOutputV12.model_validate({**base, "new_note": RawNote(kind="none")}).new_note is None
    assert output_schema("v12", True, True, True, True) is EvaluatorOutputV12
    assert output_schema("v11", True, True, True, True).__name__ == "EvaluatorOutputV11"
    assert output_schema("v8", True, False, False, False).__name__ == "EvaluatorOutputV4"
