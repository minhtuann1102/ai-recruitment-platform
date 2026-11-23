"""017 US2 review M1, M2: nap lan dau co han cho; lam moi ra rong khong duoc thay snapshot dang co JD."""
import asyncio
import logging
import time

import pytest

from app.api_error import ApiError
from fakes.fake_match_index import FakeDb, make_index, meta, vec_text


def test_default_first_load_wait_budget_is_connect_timeout_plus_five():
    index, _ = make_index(FakeDb([]))  # AI_DB_CONNECT_TIMEOUT_S = 4 trong ENV cua fake
    assert index._wait_budget_s == 9.0


def test_request_gives_up_at_the_wait_budget_but_the_shared_load_keeps_going():
    gate = asyncio.Event()  # ket noi "treo": execute khong tra ve cho toi khi gate.set()
    db = FakeDb([(vec_text(1), meta("jd:1"))], gate)
    index, _ = make_index(db, wait_budget_s=0.05)

    async def scenario():
        started = time.perf_counter()
        with pytest.raises(ApiError) as exc:
            await index.get()
        assert (exc.value.status_code, exc.value.error) == (503, "match_index_unavailable")
        assert time.perf_counter() - started < 1.0
        with pytest.raises(ApiError):  # request khac cho chung lan nap dang chay, khong mo ket noi thu hai
            await index.get()
        assert db.calls == 1
        gate.set()
        await index._first  # lan nap khong bi huy khi request dau het kien nhan
        return await index.get()

    snap = asyncio.run(scenario())
    assert snap.jobs[0].job_id == "jd:1" and db.calls == 1 and db.conns[0].closed


def test_refresh_that_comes_back_empty_keeps_the_snapshot_with_jobs(caplog):
    db = FakeDb([(vec_text(1), meta("jd:old"))])
    index, clock = make_index(db)

    async def scenario():
        old = await index.get()
        db.rows = []  # vi du: doi EMBEDDING_MODEL hoac doc giua luc dang index
        clock.t += 301
        assert await index.get() is old
        await index.refresh_task
        assert await index.get() is old and len(old) == 1
        db.rows = [(vec_text(1), meta("jd:new"))]  # lan sau co du lieu that thi doi binh thuong
        clock.t += 301
        await index.get()
        await index.refresh_task
        return await index.get()

    with caplog.at_level(logging.WARNING, logger="ai_service.matching"):
        new = asyncio.run(scenario())
    assert "match_index_refresh_empty kept=1" in caplog.text
    assert [j.job_id for j in new.jobs] == ["jd:new"] and db.calls == 3


def test_an_empty_snapshot_is_replaced_by_a_refresh_that_finds_jobs():
    db = FakeDb([])
    index, clock = make_index(db)

    async def scenario():
        empty = await index.get()  # chua index: 200 voi index_size 0 (contract)
        assert len(empty) == 0
        db.rows = [(vec_text(1), meta("jd:1"))]
        clock.t += 301
        await index.get()
        await index.refresh_task
        return await index.get()

    assert [j.job_id for j in asyncio.run(scenario()).jobs] == ["jd:1"]
