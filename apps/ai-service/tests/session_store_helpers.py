"""Ham dung chung cho test luu phien (app/session_store): mo phien, gui luot, dem Evaluator, doc checkpoint."""
import asyncio
import json
from typing import Dict, List

from app.agents.evaluator_provider import MockEvaluator
from app.turn_graph.session_graph_selector import session_graph
from app.session_store.session_checkpointer import thread_config
from conftest import parse_sse

CTX = {"track": "java_backend", "level": "junior"}


class CountingEvaluator(MockEvaluator):
    def __init__(self):
        super().__init__()
        self.calls = 0

    async def evaluate(self, inp, collector=None):
        self.calls += 1
        return await super().evaluate(inp, collector)


def start(client, sid: str) -> Dict:
    return parse_sse(client.post("/api/start", json={"session_id": sid, **CTX}).text)[-1][1]


def body(sid: str, d: Dict, answer: str, **extra) -> Dict:
    """Body slim tra loi cau hoi dang cho cua `sid` (d = done cua /start hoac next-turn truoc: chi lay turn_number).
    `plan=` van nhan de cac test cu khong phai doi cach goi, nhung bi bo: plan nam trong checkpoint."""
    extra.pop("plan", None)
    return {"session_id": sid, "turn_number": d["turn"]["turn_number"], "answer": answer, **extra}


def without_metadata(done: Dict) -> Dict:
    return {k: v for k, v in done.items() if k != "metadata"}


def stored(sid: str) -> Dict:
    return asyncio.run(session_graph().aget_state(thread_config(sid))).values


def log_lines(capsys) -> List[str]:
    return [json.loads(x)["msg"] for x in capsys.readouterr().err.splitlines() if x.startswith("{")]
