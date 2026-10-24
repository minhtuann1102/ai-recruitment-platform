"""Harness tang 3: chay cac persona qua ai-service, in chi so va ghi bao cao (design 09 muc 10.2).

  cd apps/ai-service
  python -m evals.simulate --matrix quick                     # 3 persona + 4 adversarial, simulator quy tac
  AGENT_EVALUATOR_MODE=llm ... python -m evals.simulate --matrix full --simulator llm
  python -m evals.simulate --base-url http://localhost:9080/ai   # qua gateway (TTFT that phia client)
Che do agent (mock/llm) cua ai-service theo bien moi truong AGENT_*_MODE cua tien trinh dang phuc vu.
Simulator quy tac + agent mock chi kiem harness va luong; KHONG phai so do chat luong.
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import httpx

from evals.cost_latency import load_pricing, ops_summary
from evals.personas import all_personas
from evals.sim_language import language
from evals.sim_metrics import adaptation, constraints, discrimination, injection, report_quality
from evals.simulate_session import run_session
from evals.simulator import LlmSimulator, RuleSimulator

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


def summarize(sessions: Dict[str, Dict], personas, pricing: Dict) -> Dict:
    return {"sessions": len(sessions), "discrimination": discrimination(sessions, personas),
            "adaptation": adaptation(sessions, personas), "constraints": constraints(sessions, personas),
            "report": report_quality(sessions, personas), "injection": injection(sessions, personas),
            "language": language(sessions),
            "ops": ops_summary(sessions, pricing)}


async def run_all(ids, simulator, base_url=None, duration=20, concurrency=4) -> Dict[str, Dict]:
    personas, sem, out = all_personas(), asyncio.Semaphore(concurrency), {}
    async with make_client(base_url) as client:
        async def one(pid):
            async with sem:
                try:
                    out[pid] = await run_session(client, personas[pid], simulator, duration)
                    print(f"OK   {pid} turns={len(out[pid]['turns'])} "
                          f"overall={out[pid]['report']['overall']['score']}", file=sys.stderr)
                except Exception as err:  # mot phien loi khong dung ca ma tran; ghi lai de bao cao
                    print(f"FAIL {pid}: {err}", file=sys.stderr)
        await asyncio.gather(*(one(pid) for pid in ids))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", choices=["quick", "full"], default="quick")
    parser.add_argument("--simulator", choices=["rule", "llm"], default="rule")
    parser.add_argument("--base-url")
    parser.add_argument("--duration", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    personas = all_personas()
    adv = [pid for pid, p in personas.items() if p.behaviors]
    ids = list(personas) if args.matrix == "full" else [*QUICK, *adv, "junior-nodejs-strong", "middle-nodejs-average"]
    simulator = LlmSimulator() if args.simulator == "llm" else RuleSimulator()
    sessions = asyncio.run(run_all(dict.fromkeys(ids), simulator, args.base_url, args.duration, args.concurrency))
    summary = {"run": {"matrix": args.matrix, "simulator": args.simulator, "base_url": args.base_url or "in-process",
                       "duration_min": args.duration, "failed": [p for p in ids if p not in sessions],
                       "agent_modes": {k: v for k, v in os.environ.items() if k.startswith("AGENT_")}},
               **summarize(sessions, personas, load_pricing())}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    out = args.out or REPORTS / f"eval-sim-{datetime.now():%y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "sessions": sessions}, ensure_ascii=False, indent=1), "utf-8")
    print(f"Da ghi {out}", file=sys.stderr)
    if summary["run"]["failed"]:  # phien loi bi loai khoi mau so: khong de lan chay "xanh" gia
        sys.exit(1)


if __name__ == "__main__":
    main()
