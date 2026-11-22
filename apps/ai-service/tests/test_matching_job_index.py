"""017 US2 T015: vong doi nap / lam moi snapshot chi muc JD (data-model muc 2) voi ket noi ai_db gia."""
import asyncio
import logging
from datetime import datetime, timezone

import pytest

from app.api_error import ApiError
from app.matching.job_index import JD_SQL, JobIndex
from app.matching.settings import load_match_settings
from fakes.fake_match_index import DSN, ENV, Clock, FakeDb, meta, vec_text

def make_index(db, env=None, clock=None):
    clock = clock or Clock()
    return JobIndex(load_match_settings({**ENV, **(env or {})}), connect=db, monotonic=clock,
                    now=lambda: datetime(2026, 11, 22, 9, 0, 0, tzinfo=timezone.utc)), clock



# --- nap tu ai_db ---------------------------------------------------------------------------------------------

def test_load_uses_one_short_read_only_connection_and_closes_it():
    db = FakeDb([(vec_text(1), meta("jd:1"))])
    index, _ = make_index(db)
    snap = asyncio.run(index.get())
    assert db.calls == 1 and db.conns[0].closed
    dsn, kw = db.seen[0]
    assert dsn == DSN and kw["autocommit"] is True and kw["connect_timeout"] == 4
    assert "default_transaction_read_only=on" in kw["options"] and "statement_timeout" in kw["options"]
    sql, params = db.conns[0].executed[0]
    assert sql == JD_SQL and params == ["text-embedding-3-small"]
    assert "source_type = 'job_description'" in sql and "metadata->>'dataset' = 'jd-match'" in sql
    assert "embedding_model = %s" in sql and "embedding::text" in sql
    assert snap.source == "ai_db" and snap.loaded_at == datetime(2026, 11, 22, 9, 0, 0, tzinfo=timezone.utc)
    assert snap.jobs[0].job_id == "jd:1"


def test_snapshot_is_cached_while_fresh():
    db = FakeDb([(vec_text(1), meta("jd:1"))])
    index, clock = make_index(db)

    async def scenario():
        first = await index.get()
        clock.t += 299
        return first, await index.get()

    first, second = asyncio.run(scenario())
    assert db.calls == 1 and first is second


def test_first_load_failure_is_match_index_unavailable_without_leaking_secrets():
    db = FakeDb([])
    db.fail = True
    index, _ = make_index(db)
    with pytest.raises(ApiError) as exc:
        asyncio.run(index.get())
    err = exc.value
    assert (err.status_code, err.error) == (503, "match_index_unavailable")
    assert "S3CRET" not in err.message and "db.example" not in err.message


def test_empty_db_url_in_real_mode_is_the_same_503_without_connecting():
    db = FakeDb([])
    index, _ = make_index(db, env={"AI_DB_URL": ""})
    with pytest.raises(ApiError) as exc:
        asyncio.run(index.get())
    assert (exc.value.status_code, exc.value.error) == (503, "match_index_unavailable") and db.calls == 0


def test_failed_first_load_is_not_retried_immediately_but_is_after_the_backoff():
    db = FakeDb([(vec_text(1), meta("jd:1"))])
    db.fail = True
    index, clock = make_index(db)

    async def scenario():
        for _ in range(3):  # khong moi request deu cho het connect_timeout cua Supabase
            with pytest.raises(ApiError):
                await index.get()
        assert db.calls == 1
        db.fail = False
        clock.t += 6
        return await index.get()

    snap = asyncio.run(scenario())
    assert db.calls == 2 and snap.jobs[0].job_id == "jd:1"


def test_concurrent_first_requests_share_one_load():
    gate = asyncio.Event()
    db = FakeDb([(vec_text(1), meta("jd:1"))], gate)
    index, _ = make_index(db)

    async def scenario():
        tasks = [asyncio.create_task(index.get()) for _ in range(3)]
        await asyncio.sleep(0.01)
        gate.set()
        return await asyncio.gather(*tasks)

    snaps = asyncio.run(scenario())
    assert db.calls == 1 and snaps[0] is snaps[1] is snaps[2]


# --- lam moi nen ------------------------------------------------------------------------------------------------

def test_stale_snapshot_is_served_immediately_and_refreshed_in_background():
    gate = asyncio.Event()
    db = FakeDb([(vec_text(1), meta("jd:old"))])
    index, clock = make_index(db)

    async def scenario():
        old = await index.get()
        db.rows, db.gate = [(vec_text(1), meta("jd:new"))], gate  # lan nap sau bi giu lai den khi gate.set()
        clock.t += 301
        served = await asyncio.wait_for(index.get(), 0.5)  # khong cho lan nap nen
        await asyncio.sleep(0.01)  # cho task nen toi cho gate
        assert served is old and index.refresh_task is not None and not index.refresh_task.done()
        again = await index.get()  # dang nap: khong mo lan nap thu hai
        assert again is old and db.calls == 2
        gate.set()
        await index.refresh_task
        return await index.get()

    snap = asyncio.run(scenario())
    assert [j.job_id for j in snap.jobs] == ["jd:new"] and db.calls == 2 and db.conns[1].closed


def test_refresh_failure_keeps_old_snapshot_logs_and_waits_a_full_interval(caplog):
    db = FakeDb([(vec_text(1), meta("jd:old"))])
    index, clock = make_index(db)

    async def scenario():
        old = await index.get()
        db.fail = True
        clock.t += 301
        assert await index.get() is old
        await index.refresh_task
        assert await index.get() is old and db.calls == 2  # chua toi han thu lai
        clock.t += 301
        db.fail, db.rows = False, [(vec_text(1), meta("jd:new"))]
        await index.get()
        await index.refresh_task
        return old, await index.get()

    with caplog.at_level(logging.WARNING, logger="ai_service.matching"):
        old, new = asyncio.run(scenario())
    assert "match_index_refresh_failed error=OSError" in caplog.text
    assert "db.example" not in caplog.text and "S3CRET" not in caplog.text
    assert new is not old and new.jobs[0].job_id == "jd:new" and db.calls == 3


# --- mock -------------------------------------------------------------------------------------------------------

def test_mock_mode_never_touches_the_db_and_needs_no_db_url():
    db = FakeDb([])
    index, clock = make_index(db, env={"MATCH_MOCK": "true", "AI_DB_URL": ""})
    first = asyncio.run(index.get())
    clock.t += 10_000  # mock khong het han, khong lam moi
    assert asyncio.run(index.get()) is first and db.calls == 0 and first.source == "mock"
