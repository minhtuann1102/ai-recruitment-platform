"""Chay mot phien phong van end-to-end qua HTTP nhu interview-service se lam: start -> next-turn... -> finalize.

Phase 04: ai-service giu state / plan / lich su trong checkpoint; script chi gui body slim (session_id, turn_number,
answer, elapsed_seconds) va giu plan / state / turns cuc bo de do luong va tra ket qua. Moi cau tra loi cong `30 + 0.4 x so tu` giay vao elapsed_seconds
(design 09 muc 10.2). TTFT do phia client = tu luc gui request toi event token/replace dau tien; voi ASGI
in-process (khong --base-url) httpx dem ca body nen TTFT ~ tong thoi gian, chi co y nghia khi goi service that.
"""
import json
import time
from typing import Dict, List, Optional, Tuple

import httpx

from app.models_interview import CandidateState, InterviewPlan, PlanTopic
from app.replan import effective_plan
from evals.personas import Persona

MAX_TURNS = 40
# TurnInfo (phase 04, POLICY_MODE=hybrid): quyet dinh truoc apply_action; sim_policy_metrics doc cac khoa nay;
# swap_result (phase 05, REPLAN_ENABLED): sim_replan_metrics doc
POLICY_KEYS = ("decided_by", "proposed_action", "policy_action", "overrule_reason", "action_reason", "swap_result")


async def call_sse(client: httpx.AsyncClient, path: str, body: Dict) -> Tuple[List[Tuple[str, Dict]], Dict]:
    """-> (events, timing {ttft_s | None, total_s}). Loi HTTP thi nem RuntimeError kem body."""
    events, first, started, buf = [], None, time.perf_counter(), ""
    async with client.stream("POST", path, json=body) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"{path} {resp.status_code}: {(await resp.aread())[:300]!r}")
        async for chunk in resp.aiter_text():
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                lines = block.splitlines()
                name = next((ln[7:] for ln in lines if ln.startswith("event: ")), "")
                data = json.loads(next((ln[6:] for ln in lines if ln.startswith("data: ")), "{}"))
                if name in ("token", "replace") and first is None:
                    first = time.perf_counter()
                events.append((name, data))
    total = time.perf_counter() - started
    # luot khong co token (vua tra loi cau wrap_up, khong goi LLM): ttft_s None de khong keo percentile xuong
    return events, {"ttft_s": round(first - started, 3) if first else None, "total_s": round(total, 3)}


def _done(events: List[Tuple[str, Dict]], path: str) -> Dict:
    if not events or events[-1][0] != "done":
        raise RuntimeError(f"{path}: stream khong ket thuc bang done: {events[-1:] }")
    return events[-1][1]


def _topic(plan: InterviewPlan, topic_id: Optional[str]) -> Optional[PlanTopic]:
    return next((t for ph in plan.phases for t in ph.topics if t.id == topic_id), None)


def session_id(pid: str, run: Optional[int] = None) -> str:
    """`--runs N` (N > 1): moi run co sid rieng de tai lieu ghi lai khong de nhau; run None = dinh dang cu."""
    return f"sim-{pid}" if run is None else f"sim-{pid}-r{run}"


async def run_session(client: httpx.AsyncClient, persona: Persona, simulator, duration: int = 20,
                      run: Optional[int] = None) -> Dict:
    sid = session_id(persona.id, run)
    start = {"session_id": sid, "track": persona.track, "level": persona.level, "duration_minutes": duration}
    if persona.jd_profile:  # persona co JD/CV gia (skewed): do phu yeu cau, khong chi plan theo track + level
        start["jd_profile"] = persona.jd_profile
    if persona.cv_profile:
        start["cv_profile"] = persona.cv_profile
    events, timing = await call_sse(client, "/api/start", start)
    done = _done(events, "/api/start")
    plan_json, plan = done["plan"], InterviewPlan.model_validate(done["plan"])
    state, question, turn, elapsed = done["state"], done["question"], done["turn"], 0
    calls = [{"path": "start", **timing, "metadata": done["metadata"]}]
    turns = []
    for _ in range(MAX_TURNS):
        # phase 05: topic `alt*` chi co trong plan.replan.reserve; plan thuc te = plan goc + state.swaps moi nhat
        topic = _topic(effective_plan(plan, CandidateState.model_validate(state)), turn["topic_id"])
        answer = await simulator.answer(persona, topic, question, turn["action"])
        if answer is None:  # ung vien bam ket thuc (vd go /end trong evals.play)
            state["end_reason"] = "candidate_ended"
            break
        elapsed += int(30 + 0.4 * len(answer.split()))
        body = {"session_id": sid, "turn_number": turn["turn_number"], "answer": answer, "elapsed_seconds": elapsed}
        events, timing = await call_sse(client, "/api/next-turn", body)
        nd = _done(events, "/api/next-turn")
        calls.append({"path": "next-turn", **timing, "metadata": nd["metadata"],
                      "replaced": any(n == "replace" for n, _ in events)})
        turns.append({"turn_number": turn["turn_number"], "phase": turn["phase"], "topic_id": turn["topic_id"],
                      "turn_kind": turn["turn_kind"], "difficulty": turn["difficulty"], "question": question,
                      "answer": answer, "evaluation": nd["evaluation"], "action": turn["action"],
                      "question_source": turn.get("question_source"), "qa_id": turn.get("qa_id"),
                      # phase 04 (hybrid): quyet dinh da dua ra cau hoi nay; rules thi toan None
                      **{k: turn.get(k) for k in POLICY_KEYS}})
        state = nd["state"]
        if nd["session_end"]:
            break
        if "end_early" in persona.behaviors and len(turns) >= 3:
            state["end_reason"] = "candidate_ended"
            break
        question, turn = nd["question"], nd["turn"]
    if not turns:  # ket thuc truoc khi tra loi cau nao: khong co gi de cham
        return {"persona": persona.id, "plan": plan_json, "turns": [], "report": None, "calls": calls,
                "elapsed_s": elapsed, "swaps": state.get("swaps", []), "notes": state.get("notes", [])}
    # end_reason cua body chi dung khi state luu chua co (candidate_ended: ung vien bam ket thuc giua chung)
    final = {"session_id": sid, "end_reason": state.get("end_reason") or "plan_complete", "duration_s": elapsed}
    resp = await client.post("/api/finalize", json=final)
    if resp.status_code != 200:
        raise RuntimeError(f"/api/finalize {resp.status_code}: {resp.text[:300]}")
    report = resp.json()
    fin = report.get("metadata", {})
    calls.append({"path": "finalize", "metadata": {"usage": fin.get("usage", {}),
                                                   "latency_ms": fin.get("latency_ms_by_agent", {}),
                                                   "fallbacks": report.get("meta", {}).get("fallbacks", [])}})
    return {"persona": persona.id, "plan": plan_json, "turns": turns, "report": report, "calls": calls,
            "elapsed_s": elapsed, "swaps": state.get("swaps", []), "notes": state.get("notes", [])}
