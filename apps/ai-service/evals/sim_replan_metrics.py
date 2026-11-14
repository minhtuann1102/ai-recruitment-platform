"""Chi so mo phong cho lap lai ke hoach giua buoi (phase 05, REPLAN_ENABLED). Ham thuan, khong goi mang.

Doc `plan.replan` (reserve, keep_ids), `state.swaps` cuoi phien (session["swaps"]), `turn.swap_result` va bao cao:
  swap_rate         = so phien co swap / so phien co reserve          (phien khong co reserve khong tinh)
  swap_results      = phan bo ket qua kiem cua cac de xuat doi (applied / budget / bad_drop / jd_priority / ...)
  jd_priority_violations = so swap co drop thuoc keep_ids   # BAT BIEN: phai = 0 (code da chan; sim kiem lai dau-cuoi)
  scored_topics     = trung binh so topic co luot duoc cham moi phien (swap khong duoc lam giam)
  jd_assessed_rate  = tong yeu cau JD da danh gia / tong yeu cau (chi phien co khoi requirements; do phu JD)
So sanh bat/tat co can hai lan chay (hybrid +- REPLAN_ENABLED, --runs 3): moi lan chay chi dung duoc mot co.
"""
from collections import Counter
from statistics import mean
from typing import Dict, Optional


def _scored_topics(session: Dict) -> int:
    return len({t["topic_id"] for t in session["turns"]
                if t.get("evaluation") and not t["evaluation"].get("degraded")
                and not t["evaluation"].get("transcript_low_confidence")})


def replan_summary(sessions: Dict[str, Dict]) -> Dict:
    pooled = [s for s in sessions.values() if s.get("turns")]
    with_pool = [s for s in pooled if (s["plan"].get("replan") or {}).get("reserve")]
    swapped = [s for s in with_pool if s.get("swaps")]
    violations = sum(w["drop"] in s["plan"]["replan"].get("keep_ids", []) for s in swapped for w in s["swaps"])
    reqs = [s["report"]["requirements"] for s in pooled if (s.get("report") or {}).get("requirements")]
    total = sum(r["total"] for r in reqs)
    scored = [_scored_topics(s) for s in pooled]
    rate: Optional[float] = round(len(swapped) / len(with_pool), 3) if with_pool else None
    return {
        "sessions_with_reserve": len(with_pool), "swap_sessions": len(swapped), "swap_rate": rate,
        "swaps": sum(len(s["swaps"]) for s in swapped),
        "swap_results": dict(Counter(t["swap_result"] for s in pooled for t in s["turns"] if t.get("swap_result"))),
        "jd_priority_violations": violations,
        "scored_topics": round(mean(scored), 2) if scored else None,
        "jd_assessed_rate": round(sum(r["assessed"] for r in reqs) / total, 3) if total else None}
