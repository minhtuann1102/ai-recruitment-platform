"""Do tre va chi phi tu metadata cac phien gia lap (FR-AI-080, NFR-AI-PERF01..02, COST01..03).

Gia token la GIA DINH (evals/pricing.json, USD / 1M token), kiem trang gia nha cung cap truoc khi bao cao.
"""
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

PRICING = Path(__file__).with_name("pricing.json")
COST_ALERT_USD = 0.10  # NFR-AI-COST03


def percentile(values: List[float], q: float) -> Optional[float]:
    """Percentile kieu nearest-rank (khong noi suy), du cho vai chuc mau."""
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, math.ceil(q / 100 * len(ordered)) - 1))
    return round(ordered[k], 3)


def load_pricing(path: Path = PRICING) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def session_usage(session: Dict) -> Dict[str, Dict[str, int]]:
    """Cong token theo agent qua moi call cua phien (start, next-turn, finalize)."""
    total: Dict[str, Dict[str, int]] = {}
    for call in session["calls"]:
        for agent, u in (call.get("metadata") or {}).get("usage", {}).items():
            t = total.setdefault(agent, {"input_tokens": 0, "output_tokens": 0})
            t["input_tokens"] += u.get("input_tokens", 0)
            t["output_tokens"] += u.get("output_tokens", 0)
    return total


def session_cost(usage: Dict[str, Dict[str, int]], pricing: Dict) -> float:
    cost = 0.0
    for agent, u in usage.items():
        price = pricing["agents"].get(agent, pricing["default"])
        cost += u["input_tokens"] * price["input"] / 1e6 + u["output_tokens"] * price["output"] / 1e6
    return round(cost, 5)


def ops_summary(sessions: Dict[str, Dict], pricing: Dict) -> Dict:
    streamed = [c for s in sessions.values() for c in s["calls"] if c["path"] == "next-turn" and c.get("ttft_s")]
    ttft, full = [c["ttft_s"] for c in streamed], [c["total_s"] for c in streamed]
    server: Dict[str, List[int]] = {}
    fallback_calls = calls = 0
    for s in sessions.values():
        for c in s["calls"]:
            meta = c.get("metadata") or {}
            for agent, ms in (meta.get("latency_ms") or {}).items():
                if agent != "total":
                    server.setdefault(agent, []).append(ms)
            calls += 1
            fallback_calls += bool(meta.get("fallbacks"))
    costs = {pid: session_cost(session_usage(s), pricing) for pid, s in sessions.items()}
    return {
        "ttft_s": {"p50": percentile(ttft, 50), "p95": percentile(ttft, 95), "n": len(ttft)},
        "turn_total_s": {"p50": percentile(full, 50), "p95": percentile(full, 95)},
        "server_latency_ms": {a: {"p50": percentile(v, 50), "p95": percentile(v, 95)} for a, v in server.items()},
        "fallback_call_rate": round(fallback_calls / calls, 3) if calls else None,
        "cost_usd": {"mean": round(sum(costs.values()) / len(costs), 5) if costs else None,
                     "max": max(costs.values(), default=None),
                     "over_alert": [pid for pid, c in costs.items() if c > COST_ALERT_USD]},
        "pricing_note": pricing.get("note", ""),
    }
