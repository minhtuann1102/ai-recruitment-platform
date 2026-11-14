"""Tach TTFT luot next-turn theo chang tu file phien da luu (docs 08 muc 9.2): khong goi mang, khong goi LLM.

TTFT client = RAG theo luot + Evaluator + TTFT Interviewer + overhead (chay noi tiep, app/turn_engine.py).
`metadata.latency_ms` chi co thoi gian goi LLM: evaluator (ca retry/repair), query_rewriter, embedding, interviewer
(ca stream). `other` = TTFT - evaluator - query_rewriter - embedding: TTFT Interviewer + truy van DB RAG + overhead.
Chi dung file chay `--serve` (base_url khac `in-process`): chay in-process thi ttft_s bang total_s.
Luot fallback tach rieng: Evaluator het han roi cham heuristic thi log truoc 09/11 ghi `latency_ms.evaluator` = 0 (thoi
gian cho nam het trong `other`), tu 09/11 ghi thoi gian cho; Interviewer qua han TTFT 5 s thi dung cau du phong.

Uoc tinh Evaluator hai pha (docs 08 9.2 du phong 2): hoi quy evaluator_ms ~ a + b * output_tokens, pha nong ~HOT_TOKENS
token; TTFT moi = TTFT - evaluator + (a + b * HOT_TOKENS). Lac quan: bo qua phan input lon hon do them mot call.
Chay: python -m evals.ttft_breakdown plans/reports/eval-sim-*.json (nhieu file thi in them dong `pooled` gop moi luot)
"""
import json
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List, Optional, Tuple

from evals.cost_latency import percentile

TARGET_P50_S, TARGET_P95_S = 3.5, 6.0  # NFR-AI-PERF01
HOT_TOKENS = 60
RAG_AGENTS = ("query_rewriter", "embedding")
FALLBACK_KINDS = ("evaluator_mock_heuristic", "interviewer_fallback", "evaluator_lookup_fallback")


def turn_rows(sessions: Dict[str, Dict]) -> List[Dict]:
    """Moi luot next-turn co token va co Evaluator: cac chang tinh bang giay."""
    rows = []
    for s in sessions.values():
        for c in s["calls"]:
            meta = c.get("metadata") or {}
            lat = meta.get("latency_ms") or {}
            if c["path"] != "next-turn" or not c.get("ttft_s") or "evaluator" not in lat:
                continue
            ev, rag = lat["evaluator"] / 1000, sum(lat.get(a, 0) for a in RAG_AGENTS) / 1000
            usage = (meta.get("usage") or {}).get("evaluator") or {}
            fallbacks = meta.get("fallbacks") or []
            # luot Evaluator co goi cong cu (EVALUATOR_TOOLS) tach rieng: ve them 1 round trip, khong tron vao luot thuong
            kind = next((f for f in FALLBACK_KINDS if f in fallbacks), "lookup" if usage.get("tool_calls") else "normal")
            rows.append({"kind": kind, "ttft": c["ttft_s"], "evaluator": ev, "rag_llm": rag,
                         "other": c["ttft_s"] - ev - rag, "interviewer_stream": lat.get("interviewer", 0) / 1000,
                         "ev_out": usage.get("output_tokens", 0), "ev_in": usage.get("input_tokens", 0)})
    return rows


def fit_line(xs: List[float], ys: List[float]) -> Optional[Tuple[float, float]]:
    """Hoi quy tuyen tinh y = a + b x (binh phuong toi thieu)."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    if var == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var
    return my - b * mx, b


def _pct(values: List[float]) -> Dict:
    return {"p50": percentile(values, 50), "p95": percentile(values, 95)}


def _stages(rows: List[Dict]) -> Dict:
    """Cac chang cua luot binh thuong; tail_p90: trung binh chang o 10% luot cham nhat."""
    ttft = [r["ttft"] for r in rows]
    p90 = percentile(ttft, 90)
    tail = [r for r in rows if r["ttft"] >= p90]
    return {"turns": len(rows), "ttft": _pct(ttft),
            "stages": {k: _pct([r[k] for r in rows]) for k in ("evaluator", "rag_llm", "other", "interviewer_stream")},
            "evaluator_share_median": round(median(r["evaluator"] / r["ttft"] for r in rows), 3),
            "tail_p90": {"turns": len(tail), **{k: round(sum(r[k] for r in tail) / len(tail), 3)
                                                for k in ("ttft", "evaluator", "rag_llm", "other")}},
            "evaluator_tokens": {"in_p50": percentile([r["ev_in"] for r in rows], 50),
                                 "out_p50": percentile([r["ev_out"] for r in rows], 50)}}


def breakdown(rows: List[Dict]) -> Dict:
    if not rows:
        return {"turns": 0}
    ttft = [r["ttft"] for r in rows]
    normal = [r for r in rows if r["kind"] == "normal"]
    out = {"turns": len(rows), "ttft": _pct(ttft),
           "meets_p50": round(sum(t <= TARGET_P50_S for t in ttft) / len(ttft), 3),
           "over_p95_target": round(sum(t > TARGET_P95_S for t in ttft) / len(ttft), 3),
           "fallback": {k: {"turns": len(g), "ttft_p50": percentile([r["ttft"] for r in g], 50)}
                        for k in FALLBACK_KINDS if (g := [r for r in rows if r["kind"] == k])},
           "normal": _stages(normal) if normal else {"turns": 0}}
    lookup = [r for r in rows if r["kind"] == "lookup"]
    if lookup:
        out["lookup"] = _stages(lookup)
    out["without_fallback_turns"] = _pct([r["ttft"] for r in normal])
    line = fit_line([r["ev_out"] for r in normal], [r["evaluator"] for r in normal])
    if line:
        a, b = line
        hot = a + b * HOT_TOKENS
        out["evaluator_fit"] = {"intercept_s": round(a, 3), "ms_per_output_token": round(b * 1000, 2),
                                "hot_phase_s": round(hot, 3)}
        # luot fallback giu nguyen: hai pha khong bot thoi gian cho Evaluator het han
        out["two_phase_estimate"] = _pct([r["ttft"] - r["evaluator"] + hot if r["kind"] == "normal" else r["ttft"]
                                          for r in rows])
    return out


def main(paths: List[str]) -> None:
    pooled: List[Dict] = []
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        run = data.get("summary", {}).get("run", {})
        if run.get("base_url") in (None, "in-process"):
            print(f"{Path(p).name}: bo qua (in-process, ttft_s = total_s)")
            continue
        rows = turn_rows(data["sessions"])
        pooled += rows
        print(Path(p).name, json.dumps(breakdown(rows), ensure_ascii=False))
    if len(paths) > 1:
        print("pooled", json.dumps(breakdown(pooled), ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
