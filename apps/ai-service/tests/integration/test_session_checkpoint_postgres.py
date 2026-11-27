"""Luu phien tren Postgres that (AsyncPostgresSaver). Bo qua khi khong dat SESSION_DB_TEST_URL (CI mac dinh khong co DB).

Chay: docker run -d --rm --name session_pg -e POSTGRES_PASSWORD=pg -p 5545:5432 postgres:16-alpine
      SESSION_DB_TEST_URL=postgresql://postgres:pg@localhost:5545/postgres pytest -m integration
Test tu tao bang checkpoint (setup, idempotent) tren DB thu va xoa thread cua minh sau khi chay. Pool gan voi vong su
kien: mo store, goi app (httpx ASGITransport) va dong store trong cung mot asyncio.run.
"""
import asyncio
import os
import uuid

import httpx
import pytest

pytest.importorskip("psycopg")

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402

from app.main import app  # noqa: E402
from app.session_store import session_checkpointer as store  # noqa: E402
from app.session_store.session_store_settings import load_session_store_settings  # noqa: E402
from app.turn_graph.turn_graph_builder import turn_graph  # noqa: E402
from conftest import parse_sse  # noqa: E402
from tests.session_store_helpers import CTX, body, without_metadata  # noqa: E402

URL = os.environ.get("SESSION_DB_TEST_URL")
pytestmark = [pytest.mark.integration, pytest.mark.skipif(not URL, reason="SESSION_DB_TEST_URL chua dat")]
GOOD = "Em dùng HashMap với equals và hashCode, độ phức tạp O(1) trung bình."


async def _with_postgres_store(scenario):
    settings = load_session_store_settings({"SESSION_STORE": "postgres", "SESSION_DB_URL": URL})
    pool = store.postgres_pool(settings)
    await pool.open(wait=True)
    try:
        await AsyncPostgresSaver(pool).setup()
    finally:
        await pool.close()
    await store.open_session_store(settings)
    sid = f"it-session-{uuid.uuid4().hex[:8]}"
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            return await scenario(client, sid)
    finally:
        await store.get_checkpointer().adelete_thread(sid)
        await store.close_session_store()
        store.reset_memory_store()


async def _post(client, path, json):
    r = await client.post(path, json=json)
    return r, (parse_sse(r.text) if r.headers.get("content-type", "").startswith("text/event-stream") else None)


def test_full_session_is_recorded_replayed_and_guarded_on_postgres():
    async def scenario(client, sid):
        _, start = await _post(client, "/api/start", {"session_id": sid, **CTX})
        d = start[-1][1]
        plan, done, first_body, first_done, n = d["plan"], d, None, None, 0
        while not done.get("session_end") and n < 40:
            b = body(sid, done, GOOD, plan=plan)
            _, events = await _post(client, "/api/next-turn", b)
            done, n = events[-1][1], n + 1
            if first_body is None:
                first_body, first_done = b, done
        last_body = b
        replay_r, replay = await _post(client, "/api/next-turn", last_body)
        stale_r, _ = await _post(client, "/api/next-turn", first_body)
        snap = await turn_graph().aget_state(store.thread_config(sid))
        async with store._pool.connection() as conn:
            rows = (await (await conn.execute("SELECT count(*) AS n FROM checkpoints WHERE thread_id = %s",
                                              (sid,))).fetchone())["n"]
        return n, done, first_done, replay_r, replay, stale_r, snap.values, rows

    n, done, first_done, replay_r, replay, stale_r, values, rows = asyncio.run(_with_postgres_store(scenario))
    assert n > 3 and done["session_end"]
    assert replay_r.status_code == 200 and replay[-1][1]["metadata"]["replayed"] is True
    assert without_metadata(replay[-1][1]) == without_metadata(done)
    assert stale_r.status_code == 409 and stale_r.json()["error"] == "session_invalid_state"
    assert values["state"] == done["state"] and len(values["transcript"]) == n
    assert values["last_turn"]["turn_number"] == n
    assert first_done["state"]["turn_count"] == 2 and rows == n + 1  # /start + moi luot mot checkpoint (exit)
