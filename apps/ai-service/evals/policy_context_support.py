"""PolicyContext co dinh cho `--policy-context default` cua run_evaluator / run_evaluator_sourced (phase 04).

Prompt v9 (hybrid) nhan them khoi policy_context. Mau golden khong co trang thai phong van, nen dung mot ngu canh
trung tinh (con ngan sach, chua goi y, khong con focus da hoi) de gate chat luong cham v9 vs v8: diem cua v9 khong duoc
lech so voi v8 chi vi co them ngu canh nay. [BLOCKED-KEY] chay that can khoa API.
"""
from app.agents.evaluator_input import EvaluationInput, PolicyContext


def default_policy_context() -> PolicyContext:
    return PolicyContext(left=2, hinted=False, clarifies=0, focus_used=[], covered=[], time_hint="normal",
                         difficulty=2, bounds={"min": 1, "max": 4})


def apply_policy_context(inp: EvaluationInput, mode: str) -> EvaluationInput:
    """mode: "default" thi gan ngu canh trung tinh; "none" (mac dinh) giu nguyen (v8 khong render no)."""
    if mode == "default":
        inp.policy_context = default_policy_context()
    return inp
