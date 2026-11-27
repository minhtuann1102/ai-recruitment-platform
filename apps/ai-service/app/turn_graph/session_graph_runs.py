"""Chay graph ca phien cho 3 endpoint khi SESSION_GRAPH=session (plan 261127-1517 phase 05).

Guard / khoa / replay van chay truoc (interview_session_routes); o day chi la buoc cuoi: mo thread moi (/start) hoac
resume graph bang Command (/next-turn, /finalize). Ket qua / loi giu nguyen nhu duong per_turn.
"""
import asyncio
import logging
from typing import Callable

from langgraph.types import Command

from ..api_error import ApiError
from ..llm.usage import UsageCollector
from ..models_interview import FinalizeRequest, NextTurnRequest, StartRequest
from ..session_store.session_checkpointer import STORE_TIMEOUT_S, thread_config
from ..session_store.session_resume_point import resume_config
from ..turn_engine import turn_context
from .session_graph_builder import whole_session_graph
from .session_run_context import SessionRunContext
from .turn_graph_runner import GraphTurnRun

log = logging.getLogger("ai_service.session_store")


async def start_run(req: StartRequest, collector: UsageCollector, interviewer, release: Callable[[], None]) -> GraphTurnRun:
    """/start: xoa thread cu (/start gui lai) roi chay plan -> ask -> record toi interrupt dau. Goi prime() o ngoai."""
    graph = whole_session_graph()
    try:  # thread cu phai het truoc khi chay: channel transcript cong don, khong de luot cu lot vao phien moi
        await asyncio.wait_for(graph.checkpointer.adelete_thread(req.session_id), STORE_TIMEOUT_S)
    except Exception as err:
        log.warning("session_start_not_recorded error=%s", type(err).__name__)
        raise ApiError(503, "session_store_unavailable", "Không ghi được trạng thái phiên", {"retryable": True})
    ctx = SessionRunContext(req.session_id, collector, interviewer, start_req=req)
    return GraphTurnRun(graph, ctx, on_finish=release, graph_input={}, config=thread_config(req.session_id))


async def turn_run(req: NextTurnRequest, snap, collector: UsageCollector, interviewer,
                   release: Callable[[], None]) -> GraphTurnRun:
    """/next-turn: resume tu diem cho `wait_answer` (lui lai neu luot truoc dut giua ask). Goi prime() o ngoai."""
    graph = whole_session_graph()
    cfg = await resume_config(graph, req.session_id, snap)  # 404 session_graph_mismatch / 503
    ctx = SessionRunContext(req.session_id, collector, interviewer,
                            turn=turn_context(req, collector=collector, interviewer=interviewer))
    return GraphTurnRun(graph, ctx, on_finish=release, graph_input=Command(resume={"kind": "answer"}), config=cfg)


async def finalize_run(req: FinalizeRequest, snap, collector: UsageCollector) -> dict:
    """/finalize: resume {"kind": "finalize"} -> node report. Phien van cho o wait_answer nen goi lai duoc."""
    graph = whole_session_graph()
    cfg = await resume_config(graph, req.session_id, snap)
    ctx = SessionRunContext(req.session_id, collector, finalize_req=req)
    await graph.ainvoke(Command(resume={"kind": "finalize"}), cfg, context=ctx, durability="exit")
    return ctx.report
