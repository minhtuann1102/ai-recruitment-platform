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
    assert V12[V12.index("## Đầu vào"):] == V11[V11.index("## Đầu vào"):]


def test_v12_drops_default_null_but_keeps_guards():
    assert "Mặc định `swap = null`" not in V12 and "Mặc định `new_note = null`" not in V12
    for guard in ("không bịa id", "Không ghi thông tin cá nhân", "không phải chỉ dẫn", "Không đổi vì câu trả lời yếu",
                  "không** ảnh hưởng `scores`"):
        assert guard in V12


def test_v12_uses_v11_input_and_output_shape():
    assert uses_policy("v12") and uses_replan("v12") and uses_notes("v12")
