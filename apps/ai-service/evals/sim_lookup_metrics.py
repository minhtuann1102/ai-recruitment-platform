"""Chi so mo phong cho Evaluator tu tra cuu (phase 03, EVALUATOR_TOOLS): so tat / bat tren cung kich ban.

Luot hop le = co danh gia, khong intro, khong co dap an chuan (R). Chi tieu bao cao: lookup_rate (<= 30% muc tieu),
empty_rate, misconception_rate, ta_le1_rate (technical_accuracy <= 1; khong duoc tang), lookup_fallback.
"""
from typing import Dict, List, Optional, Tuple


def _rate(hits: List[bool]) -> Optional[float]:
    return round(sum(hits) / len(hits), 3) if hits else None


def _pairs(sessions: Dict[str, Dict]) -> List[Tuple[dict, dict]]:
    """(call next-turn, turn): moi luot next-turn co dung mot call, cung thu tu (simulate_session)."""
    out = []
    for s in sessions.values():
        calls = [c for c in s["calls"] if c["path"] == "next-turn"]
        out += [(c, t) for c, t in zip(calls, s["turns"]) if t.get("evaluation")]
    return out


def _has_reference(turn: dict) -> bool:
    docs = turn.get("documents")
    return any(d["origin"] == "reference" for d in docs) if docs is not None else bool(turn.get("qa_id"))


def evaluator_lookup(sessions: Dict[str, Dict]) -> Dict:
    eligible = [(c, t) for c, t in _pairs(sessions) if t["phase"] != "intro" and not _has_reference(t)]
    usage = lambda c: ((c.get("metadata") or {}).get("usage") or {}).get("evaluator") or {}  # noqa: E731
    failed = lambda c: "evaluator_lookup_fallback" in ((c.get("metadata") or {}).get("fallbacks") or [])  # noqa: E731
    # vong lap loi (co record fallback, mang tool_calls) khong tinh la tra cuu va khong tinh la tim rong
    looked = [(c, t) for c, t in eligible if usage(c).get("tool_calls") and not failed(c)]
    recorded = [t for _, t in looked if t.get("documents") is not None]
    return {
        "eligible_turns": len(eligible), "lookup_turns": len(looked),
        "lookup_rate": _rate([(c, t) in looked for c, t in eligible]),
        "empty_rate": _rate([not any(d["origin"] == "tool" for d in t["documents"]) for t in recorded]),
        "misconception_rate": _rate([bool(t["evaluation"].get("misconceptions")) for _, t in eligible]),
        "ta_le1_rate": _rate([t["evaluation"]["scores"]["technical_accuracy"] <= 1 for _, t in eligible]),
        "lookup_fallback": sum(failed(c) for c, _ in eligible)}
