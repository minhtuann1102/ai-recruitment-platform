"""Checkpointer cua graph theo SESSION_STORE: InMemorySaver (mac dinh) hoac AsyncPostgresSaver tren pool.

Pool mo / dong trong lifespan cua app. Bang checkpoint KHONG tao luc khoi dong: chay
scripts/setup_session_checkpoint_tables.py (DE / lenh trien khai). `prepare_threshold=None`: pooler Supabase (che do
transaction) khong giu prepared statement giua cac lenh (doc 12, G9). Pool mo khong cho ket noi: DB chua san sang thi
service van len, luot doc checkpoint loi tra 503 session_store_unavailable (session_turn_guard).
"""
import logging
import os
from typing import Optional

from langgraph.checkpoint.memory import InMemorySaver

from .session_store_settings import SessionStoreSettings, load_session_store_settings

log = logging.getLogger("ai_service.session_store")
STORE_TIMEOUT_S = 3.0  # cho ket noi pool / doc checkpoint: AsyncPostgresSaver khoa chung moi lenh, DB treo khong duoc
MAX_MEMORY_SESSIONS = 500  # memory: giu toi da N phien gan nhat (co cau tra loi ung vien), xoa phien cu nhat
STRICT_ENVS = ("staging", "production")
_saver = InMemorySaver()
_pool = None


def get_checkpointer():
    return _saver


def thread_config(session_id: str) -> dict:
    """Moi phien mot thread LangGraph: thread_id = session_id."""
    return {"configurable": {"thread_id": session_id}}


def reset_memory_store() -> None:
    """Test: moi test mot InMemorySaver moi (phien cua test truoc khong lam lech guard)."""
    global _saver
    _saver = InMemorySaver()


def postgres_pool(settings: SessionStoreSettings):
    """Pool cho AsyncPostgresSaver (can autocommit + dict_row); chua mo."""
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool
    return AsyncConnectionPool(settings.db_url, min_size=1, max_size=settings.pool_max_size, open=False,
                               timeout=STORE_TIMEOUT_S, kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row})


async def open_session_store(settings: Optional[SessionStoreSettings] = None) -> None:
    """Goi trong lifespan truoc khi compile graph. Cau hinh sai (ConfigError) thi khong khoi dong."""
    global _saver, _pool
    settings = settings or load_session_store_settings()
    if settings.kind == "memory":
        if os.environ.get("APP_ENV", "dev").lower() in STRICT_ENVS:  # chay song song (phase 03): chi canh bao
            log.warning("session_store_memory_in_strict_env max_sessions=%d", MAX_MEMORY_SESSIONS)
        log.info("session_store kind=memory")
        return
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    _pool = postgres_pool(settings)
    await _pool.open(wait=False)
    _saver = AsyncPostgresSaver(_pool)
    log.info("session_store kind=postgres pool_max=%d", settings.pool_max_size)


async def close_session_store() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def prune_memory_store() -> None:
    """memory: qua MAX_MEMORY_SESSIONS phien thi xoa phien ghi dau tien cu nhat (khong de RAM giu moi phien)."""
    if not isinstance(_saver, InMemorySaver):
        return
    for thread_id in list(_saver.storage)[:max(0, len(_saver.storage) - MAX_MEMORY_SESSIONS)]:
        await _saver.adelete_thread(thread_id)
