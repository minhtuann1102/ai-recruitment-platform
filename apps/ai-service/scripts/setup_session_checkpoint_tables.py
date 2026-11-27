"""Tao / nang cap bang checkpoint LangGraph cho luu phien (plan 261127-1517 phase 03). Chay mot lan moi lan trien
khai (DE / lenh deploy), KHONG chay luc app khoi dong:

    cd apps/ai-service && SESSION_DB_URL=postgresql://... .venv/bin/python -m scripts.setup_session_checkpoint_tables

AsyncPostgresSaver.setup() tao bang checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations (idempotent,
chay lai chi ap migration con thieu). Can quyen CREATE tren schema; setup dung CREATE INDEX CONCURRENTLY nen ket noi
phai autocommit (pool cua app da dat).
"""
import asyncio
import os
import sys

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.session_store.session_checkpointer import postgres_pool
from app.session_store.session_store_settings import load_session_store_settings


async def main() -> None:
    settings = load_session_store_settings({**os.environ, "SESSION_STORE": "postgres"})
    pool = postgres_pool(settings)
    await pool.open(wait=True)
    try:
        await AsyncPostgresSaver(pool).setup()
    finally:
        await pool.close()
    print("session checkpoint tables ready")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:  # chi in ten loi: thong bao cua psycopg co the chua mot phan chuoi ket noi
        print(f"setup failed: {type(err).__name__}", file=sys.stderr)
        sys.exit(1)
