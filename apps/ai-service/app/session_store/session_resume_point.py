"""Diem resume cua graph ca phien (phase 05): checkpoint gan nhat dang cho o node `wait_answer`.

Binh thuong checkpoint moi nhat da la diem do (graph dung o interrupt). Moi lan chay loi / bi ngat (perceive 409 / 422,
stream dut giua `ask`, Reporter loi) van ghi them mot checkpoint con (durability="exit"), nen checkpoint moi nhat co
the co next=('ask',) / ('perceive',)... Khi do lan theo `parent_config` tu checkpoint moi nhat toi checkpoint dau tien co
next == ('wait_answer',) va resume tu checkpoint_id do: chay lai ca luot, giong phase 03 (Lech 1). Moi lan resume deu
tu diem cho nen cac checkpoint loi la anh em, chuoi cha ngan (khong quet lich su ca thread). Khong tim duoc (thread do
graph mot luot ghi vi doi SESSION_GRAPH giua phien, hoac /start bi huy) -> 404 session_not_found, log
session_not_resumable.
"""
import asyncio
import logging

from ..api_error import ApiError
from .session_checkpointer import STORE_TIMEOUT_S, thread_config

log = logging.getLogger("ai_service.session_store")
WAIT_NODE = "wait_answer"
MAX_HOPS = 20  # chuoi cha tu checkpoint loi toi diem cho chi dai vai buoc; chan vong lap bat thuong


async def _find(graph, session_id: str, snap) -> dict:
    if snap is None:  # sau khi ghi them checkpoint (record_finalize_end) snapshot cu khong con dung: doc lai
        snap = await graph.aget_state(thread_config(session_id))
    if snap.next == (WAIT_NODE,):
        return thread_config(session_id)
    for _ in range(MAX_HOPS):
        if not snap.parent_config:
            return {}
        snap = await graph.aget_state(snap.parent_config)
        if snap.next == (WAIT_NODE,):
            return snap.config
    return {}


async def resume_config(graph, session_id: str, snap) -> dict:
    """Config de gui Command(resume=...): thread (khi checkpoint moi nhat da cho) hoac thread + checkpoint_id phai lui.
    `snap`: StateSnapshot moi nhat vua doc o stored_snapshot, de duong thuong khong doc them; None thi doc lai."""
    try:
        cfg = await asyncio.wait_for(_find(graph, session_id, snap), 2 * STORE_TIMEOUT_S)
    except Exception as err:
        log.warning("session_store_unavailable error=%s", type(err).__name__)
        raise ApiError(503, "session_store_unavailable", "Không đọc được trạng thái phiên", {"retryable": True})
    if not cfg:
        log.warning("session_not_resumable")
        raise ApiError(404, "session_not_found", "Không tìm thấy phiên phỏng vấn")
    return cfg
