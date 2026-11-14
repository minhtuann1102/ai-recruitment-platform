"""Chi so mo phong cho policy lai (phase 04, POLICY_MODE=hybrid): do dong y va ty le bac de xuat cua LLM.

Doc cac khoa TurnInfo da chep vao turns (simulate_session.POLICY_KEYS). Luot chi tinh khi co de xuat
(proposed_action != null) va khong phai forced (forced / low_performance dung tren LLM, khong phai do bac):
  agreement     = mean(proposed_action == policy_action)   # policy_action = luat decide() (phan thuc cua luat)
  overrule_rate = mean(overrule_reason != null)             # muc tieu <= 15% (phase 04)
Chay rules thi moi khoa None: tra `{"proposal_turns": 0, ...}` (khong co gi de do).
"""
from collections import Counter
from typing import Dict, List, Optional


def _rate(hits: List[bool]) -> Optional[float]:
    return round(sum(hits) / len(hits), 3) if hits else None


def hybrid_policy(sessions: Dict[str, Dict]) -> Dict:
    turns = [t for s in sessions.values() for t in s["turns"]]
    decided = [t for t in turns if t.get("decided_by")]
    proposals = [t for t in decided if t.get("proposed_action") and t["decided_by"] != "forced"]
    return {
        "decided_turns": len(decided), "forced_turns": sum(t["decided_by"] == "forced" for t in decided),
        "proposal_turns": len(proposals),
        "agreement": _rate([t["proposed_action"] == t.get("policy_action") for t in proposals]),
        "overrule_rate": _rate([bool(t.get("overrule_reason")) for t in proposals]),
        "overrule_reasons": dict(Counter(t["overrule_reason"] for t in proposals if t.get("overrule_reason"))),
        "proposed_actions": dict(Counter(t["proposed_action"] for t in proposals)),
        "policy_actions": dict(Counter(t["policy_action"] for t in proposals if t.get("policy_action"))),
        "decided_by": dict(Counter(t["decided_by"] for t in decided))}
