"""Harness tang 3: chay cac persona qua ai-service, in chi so va ghi bao cao (design 09 muc 10.2).

  cd apps/ai-service
  python -m evals.simulate --matrix quick                     # 3 persona + 4 adversarial, simulator quy tac
  AGENT_EVALUATOR_MODE=llm ... python -m evals.simulate --matrix full --simulator llm
  python -m evals.simulate --base-url http://localhost:9080/ai   # qua gateway (TTFT that phia client)
  python -m evals.simulate --serve                            # service that trong tien trinh: TTFT that + `documents`
Che do agent (mock/llm) cua ai-service theo bien moi truong AGENT_*_MODE cua tien trinh dang phuc vu.
Simulator quy tac + agent mock chi kiem harness va luong; KHONG phai so do chat luong.
"""
import argparse
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, List

import httpx
import uvicorn

from app.plan_snippets import warm_rag
from evals.cost_latency import load_pricing, ops_summary
from evals.personas import all_personas, skewed_personas
from evals.sim_language import language
from evals.sim_lookup_metrics import evaluator_lookup
from evals.sim_policy_metrics import hybrid_policy
from evals.sim_replan_metrics import replan_summary
from evals.sim_style import session_style
from evals.sim_metrics import (adaptation, constraints, discrimination, end_reasons, grounding, grounding_breakdown,
                               injection, question_bank, rag_health, report_quality)
from evals.sim_runs import summarize_runs
from evals.simulate_session import run_session
from evals.simulator import LlmSimulator, RuleSimulator
from evals.turn_source_recorder import attach_documents, record_documents

REPORTS = Path(__file__).resolve().parents[3] / "plans" / "reports"
QUICK = ("junior-java-strong", "junior-java-average", "junior-java-weak")


def make_client(base_url: str = None) -> httpx.AsyncClient:
    headers = {}
    token = os.environ.get("AI_SERVICE_INTERNAL_TOKEN")
    if token:
        headers["X-Internal-Token"] = token
    if base_url:
        return httpx.AsyncClient(base_url=base_url, headers=headers, timeout=120)
    from app.main import app  # in-process: khong can chay server

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ai", headers=headers,
                             timeout=120)


@asynccontextmanager
async def local_server() -> AsyncIterator[str]:
    """Chay service qua socket ngay trong tien trinh: ASGI in-process dem ca body nen TTFT = tong thoi gian luot, va
    khong chay lifespan (nap corpus BM25). Cung tien trinh thi record_documents van doc duoc dau vao Evaluator."""
    from app.main import app

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None, access_log=False))
    task = asyncio.ensure_future(server.serve())
    while not server.started:
        if task.done():
            await task  # neu serve() loi thi hien loi that
            raise RuntimeError("uvicorn khong khoi dong duoc")
        await asyncio.sleep(0.05)
    await warm_rag()  # nhu service da chay lau: khong do trung luc corpus BM25 chua nap
    try:
        yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
    finally:
        server.should_exit = True
        await task


def summarize(sessions: Dict[str, Dict], personas, pricing: Dict) -> Dict:
    return {"sessions": len(sessions), "discrimination": discrimination(sessions, personas),
            "adaptation": adaptation(sessions, personas), "constraints": constraints(sessions, personas),
            "end_reasons": end_reasons(sessions, personas), "report": report_quality(sessions, personas),
            "injection": injection(sessions, personas),
            "language": language(sessions), "question_bank": question_bank(sessions), "style": session_style(sessions),
            "grounding": grounding(sessions), "grounding_breakdown": grounding_breakdown(sessions),
            "rag_health": rag_health(sessions), "evaluator_lookup": evaluator_lookup(sessions),
            "hybrid_policy": hybrid_policy(sessions), "replan": replan_summary(sessions), "ops": ops_summary(sessions, pricing)}


def known_personas() -> Dict:
    """Ma tran 29 persona + persona skewed (chi chay khi chon ro: `--matrix skewed`)."""
    return {**all_personas(), **skewed_personas()}


async def run_all(ids, simulator, base_url=None, duration=20, concurrency=4, serve=False,
                  run=None) -> Dict[str, Dict]:
    """`run`: so thu tu run khi `--runs N` > 1 (sid `sim-{pid}-r{run}`); None = mot run, sid cu."""
    personas, sem, out = known_personas(), asyncio.Semaphore(concurrency), {}

    async def play(url):
        async with make_client(url) as client:
            async def one(pid):
                async with sem:
                    try:
                        out[pid] = await run_session(client, personas[pid], simulator, duration, run)
                        print(f"OK   {pid} turns={len(out[pid]['turns'])} "
                              f"overall={out[pid]['report']['overall']['score']}", file=sys.stderr)
                    except Exception as err:  # mot phien loi khong dung ca ma tran; ghi lai de bao cao
                        print(f"FAIL {pid}: {err}", file=sys.stderr)
            await asyncio.gather(*(one(pid) for pid in ids))

    with record_documents() as seen:
        if serve:
            async with local_server() as url:
                await play(url)
        else:
            await play(base_url)
    attach_documents(out, seen, run)
    return out


async def run_many(ids, simulator, args, runs: int) -> List[Dict[str, Dict]]:
    """Moi run noi tiep trong CUNG mot event loop: gateway LLM la singleton giu pool httpx gan voi loop dau tien,
    asyncio.run moi run se de run sau dung ket noi cua loop da dong."""
    return [await run_all(ids, simulator, args.base_url, args.duration, args.concurrency, args.serve,
                          run=i if runs > 1 else None) for i in range(1, runs + 1)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", choices=["quick", "full", "skewed"], default="quick")
    parser.add_argument("--runs", type=int, default=1, help="so lan chay lai ca ma tran (sid rieng moi run); "
                        "N > 1 thi in them stdev gop + CI bootstrap + gap strong-weak")
    parser.add_argument("--simulator", choices=["rule", "llm"], default="rule")
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--base-url")
    target_group.add_argument("--serve", action="store_true", help="service qua socket trong tien trinh (TTFT that)")
    parser.add_argument("--duration", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs phai >= 1")
    personas = known_personas()
    adv = [pid for pid, p in all_personas().items() if p.behaviors]
    ids = (list(all_personas()) if args.matrix == "full" else list(skewed_personas()) if args.matrix == "skewed"
           else [*QUICK, *adv, "junior-nodejs-strong", "middle-nodejs-average"])
    ids = list(dict.fromkeys(ids))
    simulator = LlmSimulator() if args.simulator == "llm" else RuleSimulator()
    runs = args.runs
    by_run = asyncio.run(run_many(ids, simulator, args, runs))
    target = args.base_url or ("local-server" if args.serve else "in-process")
    missing = [(i, p) for i, sessions in enumerate(by_run, 1) for p in ids if p not in sessions]
    failed = ([p for p in ids if any(p not in s for s in by_run)] if runs == 1
              else [{"run": i, "persona": p} for i, p in missing])  # N > 1: biet run nao hong
    run_info = {"matrix": args.matrix, "simulator": args.simulator, "base_url": target, "runs": runs,
                "duration_min": args.duration, "failed": failed,
                "agent_modes": {k: v for k, v in os.environ.items() if k.startswith("AGENT_")}}
    pricing = load_pricing()
    if runs == 1:  # dinh dang cu
        summary = {"run": run_info, **summarize(by_run[0], personas, pricing)}
        payload = {"summary": summary, "sessions": by_run[0]}
    else:
        summary = {"run": run_info, "pooled": summarize_runs(by_run, personas),
                   "per_run": [summarize(s, personas, pricing) for s in by_run]}
        payload = {"summary": summary, "sessions_by_run": by_run}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    out = args.out or REPORTS / f"eval-sim-{datetime.now():%y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), "utf-8")
    print(f"Da ghi {out}", file=sys.stderr)
    violations = [r["replan"]["jd_priority_violations"] for r in ([summary] if runs == 1 else summary["per_run"])]
    if any(violations):  # bat bien phase 05: khong swap nao bo topic JD uu tien
        print("FAIL swap bo topic JD uu tien (jd_priority_violations > 0)", file=sys.stderr)
        sys.exit(1)
    if failed:  # phien loi bi loai khoi mau so: khong de lan chay "xanh" gia
        sys.exit(1)


if __name__ == "__main__":
    main()
