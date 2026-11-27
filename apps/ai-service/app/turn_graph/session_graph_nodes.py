"""Node rieng cua graph ca phien (plan 261127-1517 phase 05): plan, wait_answer, report, ask, record va 5 node buoc.

Node buoc (perceive / reask / evaluate / decide / act) goi thang app/turn_steps tren `runtime.context.turn`. State graph
giu nguyen kieu cua graph mot luot (TurnGraphState); du lieu luot di qua SessionRunContext nhu o phase 02.
"""
from contextlib import aclosing

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from .. import turn_engine
from ..agents.reporter import get_reporter
from ..question_stream import turn_question_events
from ..replan import effective_plan
from ..session_store.session_record import start_values, turn_values
from ..turn_steps import act_step, decide_step, evaluate_step, perceive_step, reask_step
from .session_run_context import SessionRunContext
from .turn_graph_nodes import TurnGraphState

Rt = Runtime[SessionRunContext]
WAIT_ANSWER = "wait_answer"


async def plan_node(s: TurnGraphState, runtime: Rt) -> dict:
    """/start: Planner + RAG + cau dau (turn_engine.start_session); loi (LLM, 422...) nem ra truoc khi mo response."""
    ctx = runtime.context
    ctx.start_result = await turn_engine.start_session(ctx.start_req, collector=ctx.collector)
    return {}


async def wait_answer_node(s: TurnGraphState, runtime: Rt) -> dict:
    """Cho ung vien: graph dung o day giua cac luot. Node chay lai tu dau khi resume nen KHONG lam gi truoc interrupt.
    Gia tri resume {"kind": "answer" | "finalize"} chi de re nhanh; du lieu luot nam trong context."""
    resume = interrupt({"waiting": "answer"})
    return {"route": resume["kind"]}


async def perceive_node(s: TurnGraphState, runtime: Rt) -> dict:
    return {"route": perceive_step(runtime.context.turn)}


async def reask_node(s: TurnGraphState, runtime: Rt) -> dict:
    reask_step(runtime.context.turn)
    return {}


async def evaluate_node(s: TurnGraphState, runtime: Rt) -> dict:
    await evaluate_step(runtime.context.turn)
    return {}


async def decide_node(s: TurnGraphState, runtime: Rt) -> dict:
    return {"route": decide_step(runtime.context.turn)}


async def act_node(s: TurnGraphState, runtime: Rt) -> dict:
    act_step(runtime.context.turn)
    return {}


async def ask_node(s: TurnGraphState, runtime: Rt) -> dict:
    """Interviewer dien dat cau hoi (cau dau cua /start hoac cau cua luot); event day qua stream writer."""
    ctx, write = runtime.context, get_stream_writer()
    async with aclosing(turn_question_events(ctx.result, ctx.interviewer, ctx.collector)) as events:
        async for name, data in events:
            write((name, data))
    return {}


async def record_node(s: TurnGraphState, runtime: Rt) -> dict:
    """Xong cau hoi (hoac phien ket thuc): ghi checkpoint. /start ghi start_values, luot ghi turn_values."""
    ctx = runtime.context
    if ctx.turn is None:
        return start_values(ctx.start_req, ctx.start_result)
    return turn_values(s, ctx.turn.req, ctx.turn.result)


async def report_node(s: TurnGraphState, runtime: Rt) -> dict:
    """/finalize: Reporter viet bao cao tu request dung tu checkpoint. Phien da duoc chot done truoc khi vao graph
    (record_finalize_end o endpoint, nhu per_turn) nen node chi bao cao; goi lai thi bao cao lai."""
    ctx = runtime.context
    req = ctx.finalize_req
    req = req.model_copy(update={"plan": effective_plan(req.plan, req.state)})  # topic da doi (state.swaps)
    ctx.report = await get_reporter().report(req, ctx.collector)
    return {}
