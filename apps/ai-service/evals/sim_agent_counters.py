"""Dem de xuat tho cua Evaluator v10/v11 trong mot run sim (service chay trong tien trinh: in-process hoac --serve).

File sim chi luu ket qua sau khi code kiem (state.swaps, state.notes, turn.swap_result), nen khi = 0 khong biet LLM
tra null hay code bo. Ham nay doc chenh lech counter Prometheus cua chinh tien trinh truoc/sau mot run:
  replan.offered        = {null, proposed, degraded}: luot prompt v10+ co replan_context va LLM tra gi (null = khong
                          de xuat doi topic; degraded = LLM loi)
  replan.results        = ket qua code kiem moi de xuat swap (applied / ly do bac), ke ca swap LLM tu y de xuat o
                          luot KHONG co replan_context (nen khong lay offered tru results)
  notes.recorded / notes.dropped = ghi chu LLM de xuat da luu / bi code bo (theo ly do); ca hai = 0 -> LLM luon null
--base-url (service o tien trinh khac) thi counter khong doi: tra None.
"""
from typing import Dict, Optional

from prometheus_client import REGISTRY

_NAMES = {"offered": "ai_replan_offered", "swaps": "ai_replan_swaps", "recorded": "ai_notes_recorded",
          "dropped": "ai_notes_dropped"}


def snapshot() -> Dict[str, Dict[str, float]]:
    """{ten ngan: {nhan: gia tri}} cua cac counter `_total`; nhan rong cho counter khong co label."""
    wanted = {v: k for k, v in _NAMES.items()}
    out: Dict[str, Dict[str, float]] = {k: {} for k in _NAMES}
    for family in REGISTRY.collect():
        key = wanted.get(family.name)
        if key is None:
            continue
        for s in family.samples:
            if s.name.endswith("_total"):
                out[key]["/".join(s.labels.values())] = s.value
    return out


def _delta(before: Dict[str, float], after: Dict[str, float]) -> Dict[str, int]:
    return {k: int(v - before.get(k, 0)) for k, v in after.items() if v - before.get(k, 0)}


def counters_delta(before: Dict, after: Dict, in_process: bool) -> Optional[Dict]:
    """Chenh lech mot run; None khi service o tien trinh khac (--base-url)."""
    if not in_process:
        return None
    d = {k: _delta(before[k], after[k]) for k in _NAMES}
    return {"replan": {"offered": d["offered"], "results": d["swaps"]},
            "notes": {"recorded": d["recorded"], "dropped": d["dropped"],
                      "proposed": sum(d["recorded"].values()) + sum(d["dropped"].values())}}
