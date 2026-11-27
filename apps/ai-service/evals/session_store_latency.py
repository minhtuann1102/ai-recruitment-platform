"""Do do tre luu phien (plan 261127-1517 phase 06): graph + checkpoint, KHONG goi LLM (agent ep mock, simulator quy tac).

  cd apps/ai-service
  python -m evals.session_store_latency --sessions 10 --out /tmp/latency.json                  # chi memory
  python -m evals.session_store_latency --sessions 10 --db-url postgresql://... --out ...      # them postgres

Moi to hop SESSION_STORE x SESSION_GRAPH chay N phien mock lien tiep (concurrency 1, service that qua socket nen TTFT la
that, co chay lifespan: mo store). Moi request next-turn do TTFT, tong, tong thoi gian doc / ghi checkpoint (tu
CheckpointTimingMixin). Cuoi moi to hop: so checkpoint + byte / phien (postgres) va muc phinh khi N lan tra loi loi
(voice_no_speech, 422) - review phase 05 M3. Chi in so, khong co noi dung cau tra loi. Bang checkpoint phai co san
(scripts.setup_session_checkpoint_tables). Postgres local khac Supabase / staging: do lai khi DE dung DB.
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

os.environ["RAG_ENABLED"] = "false"
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
for _agent in ("CV_PARSER", "JD_PARSER", "PLANNER", "EVALUATOR", "INTERVIEWER", "REPORTER"):
    os.environ[f"AGENT_{_agent}_MODE"] = "mock"  # ep mock: do overhead thuan, khong ton token

import evals.simulate_session as sim_session
from app.session_store import session_checkpoint_timing as timing
from app.session_store.session_checkpointer import get_checkpointer, reset_memory_store
from evals.cost_latency import percentile
from evals.personas import all_personas
from evals.simulate import local_server, make_client
from evals.simulator import RuleSimulator

PERSONA = "junior-java-average"
CHECKPOINT_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")
_bucket: List = []  # (op, giay) cua request dang chay; concurrency 1 nen khong lan request
_calls: List[Dict] = []  # so do moi request next-turn cua to hop dang chay


def _install_recorders() -> None:
    """Gan lai observe_checkpoint (ghi them vao _bucket) va call_sse (gom so do moi request next-turn)."""
    original_observe, original_call = timing.observe_checkpoint, sim_session.call_sse

    def observe(op, store, seconds):
        _bucket.append((op, seconds))
        original_observe(op, store, seconds)

    async def call(client, path, body):
        _bucket.clear()
        events, t = await original_call(client, path, body)
        if path == "/api/next-turn":
            sums = {op: sum(s for o, s in _bucket if o == op) * 1000 for op in ("read", "write")}
            counts = {op: sum(1 for o, _ in _bucket if o == op) for op in ("read", "write")}
            _calls.append({"ttft_ms": None if t["ttft_s"] is None else t["ttft_s"] * 1000,  # None: luot wrap-up khong co token
                           "total_ms": t["total_s"] * 1000,
                          "read_ms": sums["read"], "write_ms": sums["write"], "reads": counts["read"],
                          "writes": counts["write"]})
        return events, t

    timing.observe_checkpoint, sim_session.call_sse = observe, call


def storage_stats(kind: str, db_url: str, sid: str) -> Dict[str, int]:
    """So checkpoint (+ byte, postgres) cua mot phien; memory dem so checkpoint trong saver."""
    if kind == "memory":
        storage = get_checkpointer().storage.get(sid, {})
        return {"checkpoints": sum(len(v) for v in storage.values()), "bytes": 0}
    import psycopg
    with psycopg.connect(db_url) as conn:
        count = conn.execute("SELECT count(*) FROM checkpoints WHERE thread_id = %s", (sid,)).fetchone()[0]
        size = sum(conn.execute(f"SELECT coalesce(sum(pg_column_size(t.*)), 0) FROM {tbl} t WHERE thread_id = %s",
                                (sid,)).fetchone()[0] for tbl in CHECKPOINT_TABLES)
    return {"checkpoints": count, "bytes": int(size)}


async def failed_growth(client, kind: str, db_url: str, attempts: int, tag: str) -> Dict:
    """Them `attempts` lan tra loi voice_no_speech (422) vao mot phien moi: checkpoint / byte tang bao nhieu."""
    sid = f"lat-fail-{tag}"
    resp = await client.post("/api/start", json={"session_id": sid, "track": "java_backend", "level": "junior"})
    turn = json.loads(next(ln[6:] for ln in reversed(resp.text.splitlines()) if ln.startswith("data: ")))["turn"]
    before, codes = storage_stats(kind, db_url, sid), []
    for _ in range(attempts):
        r = await client.post("/api/next-turn", json={"session_id": sid, "turn_number": turn["turn_number"],
                                                      "answer": "ừm", "answer_source": "voice", "elapsed_seconds": 30})
        codes.append(r.status_code)
    after = storage_stats(kind, db_url, sid)
    return {"attempts": attempts, "status_codes": sorted(set(codes)), "before": before, "after": after,
            "added_checkpoints": after["checkpoints"] - before["checkpoints"], "added_bytes": after["bytes"] - before["bytes"]}


def summarize(calls: List[Dict], per_session: List[Dict]) -> Dict:
    def pct(key, q):
        return percentile([c[key] for c in calls if c[key] is not None], q)
    both = [c["read_ms"] + c["write_ms"] for c in calls]
    n = len(per_session) or 1
    return {"next_turn_requests": len(calls),
            **{f"{k}_p{q}": pct(f"{k}_ms", q) for k in ("ttft", "total", "read", "write") for q in (50, 95)},
            "read_write_p50": percentile(both, 50), "read_write_p95": percentile(both, 95),
            "checkpoints_per_session": round(sum(s["checkpoints"] for s in per_session) / n, 1),
            "db_bytes_per_session": round(sum(s["bytes"] for s in per_session) / n)}


async def run_combo(kind: str, mode: str, args) -> Dict:
    os.environ.update(SESSION_STORE=kind, SESSION_GRAPH=mode, SESSION_DB_URL=args.db_url or "")
    reset_memory_store()
    _calls.clear()
    per_session, failed = [], []
    persona = all_personas()[PERSONA]
    async with local_server() as url:
        async with make_client(url) as client:
            for i in range(args.sessions + 1):  # phien dau la warm-up (ket noi pool, import lazy): bo khoi so lieu
                if i == 1:
                    _calls.clear()
                tag = f"{kind}-{mode}-{i}"
                try:
                    await sim_session.run_session(client, persona, RuleSimulator(), 20, tag)
                except Exception as err:
                    failed.append(str(err)[:120])
                    continue
                if i:
                    per_session.append(storage_stats(kind, args.db_url, sim_session.session_id(persona.id, tag)))
            growth = await failed_growth(client, kind, args.db_url, args.failed_attempts, f"{kind}-{mode}")
    return {"store": kind, "graph": mode, "sessions": len(per_session), "failed_sessions": failed,
            **summarize(_calls, per_session), "failed_attempt_growth": growth}


def print_table(rows: List[Dict]) -> None:
    cols = ("ttft_p50", "ttft_p95", "total_p50", "total_p95", "read_p50", "read_p95", "write_p50", "write_p95",
            "read_write_p95", "checkpoints_per_session", "db_bytes_per_session")
    print("store/graph".ljust(20) + " ".join(c.rjust(9) for c in cols))
    for r in rows:
        print(f"{r['store']}/{r['graph']}".ljust(20) + " ".join(str(r[c]).rjust(9) for c in cols))
    for r in rows:
        g = r["failed_attempt_growth"]
        print(f"fail {r['store']}/{r['graph']}: {g['attempts']}x {g['status_codes']} -> +{g['added_checkpoints']} "
              f"checkpoint, +{g['added_bytes']} byte")


async def main_async(args) -> List[Dict]:
    _install_recorders()
    return [await run_combo(kind, mode, args) for kind in args.stores for mode in ("per_turn", "session")]


def main() -> None:
    logging.disable(logging.INFO)  # bo log request_done moi request
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=10)
    parser.add_argument("--failed-attempts", type=int, default=10)
    parser.add_argument("--db-url", help="Postgres da co bang checkpoint: them to hop SESSION_STORE=postgres")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.stores = ["memory", *(["postgres"] if args.db_url else [])]
    rows = asyncio.run(main_async(args))
    print_table(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"sessions_per_combo": args.sessions, "rows": rows}, indent=1), "utf-8")
    print(f"Da ghi {args.out}", file=sys.stderr)
    if any(r["failed_sessions"] for r in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
