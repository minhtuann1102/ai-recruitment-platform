"""Do thoi gian doc / ghi checkpoint (metric ai_session_checkpoint_seconds{op, store}), phase 06 plan 261127-1517.

Mixin boc cac ham async cua saver LangGraph: aget_tuple -> read, aput + aput_writes -> write, alist -> list. Graph
goi saver tu ben trong (ghi checkpoint sau moi node) nen chi boc o day moi bat duoc ca luot ghi trong graph.
Khong doi hanh vi: goi super() roi chi do thoi gian (ke ca khi loi, de DB cham / treo van hien tren metric).
"""
import time

from langgraph.checkpoint.memory import InMemorySaver

from ..metrics import observe_checkpoint


class CheckpointTimingMixin:
    store_label = "memory"

    async def aget_tuple(self, config):
        started = time.perf_counter()
        try:
            return await super().aget_tuple(config)
        finally:
            observe_checkpoint("read", self.store_label, time.perf_counter() - started)

    async def aput(self, config, checkpoint, metadata, new_versions):
        started = time.perf_counter()
        try:
            return await super().aput(config, checkpoint, metadata, new_versions)
        finally:
            observe_checkpoint("write", self.store_label, time.perf_counter() - started)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        started = time.perf_counter()
        try:
            return await super().aput_writes(config, writes, task_id, task_path)
        finally:
            observe_checkpoint("write", self.store_label, time.perf_counter() - started)

    async def alist(self, config, *, filter=None, before=None, limit=None):
        started = time.perf_counter()
        try:
            async for item in super().alist(config, filter=filter, before=before, limit=limit):
                yield item
        finally:
            observe_checkpoint("list", self.store_label, time.perf_counter() - started)


class TimedInMemorySaver(CheckpointTimingMixin, InMemorySaver):
    store_label = "memory"


def timed_postgres_saver_class():
    """Import tre: langgraph-checkpoint-postgres chi can khi SESSION_STORE=postgres."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    class TimedPostgresSaver(CheckpointTimingMixin, AsyncPostgresSaver):
        store_label = "postgres"

    return TimedPostgresSaver
