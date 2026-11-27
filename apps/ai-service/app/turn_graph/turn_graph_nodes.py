"""Node cua graph mot luot: moi node goi dung mot buoc cua app/turn_steps (Perceive / Evaluate / Decide / Act), stream
cau hoi (node `ask`) hoac ghi phien (node `record`).

TurnContext cua luot di qua runtime context (`astream(..., context=ctx)`), KHONG nam trong state graph: context khong
luu vao checkpoint (object co collector / ham, khong serialize duoc). State graph chi co `route` (canh tiep) va cac
key lau dai cua phien (app/session_store/session_record), chi node `record` ghi. Moi node la async: tranh LangGraph
day ham sync sang thread pool.
"""
import operator
from contextlib import aclosing
from typing import Annotated, Optional, TypedDict

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from ..question_stream import turn_question_events
from ..session_store.session_record import turn_values
from ..turn_steps import TurnContext, act_step, decide_step, evaluate_step, perceive_step, reask_step


class TurnGraphState(TypedDict, total=False):
    route: str  # perceive: session_end | reask | evaluate; decide: session_end | follow_up | hint | next_topic | ...
    session: dict
    plan: dict
    state: dict
    question: str
    turn: dict
    transcript: Annotated[list, operator.add]
    last_turn: Optional[dict]


async def perceive_node(s: TurnGraphState, runtime: Runtime[TurnContext]) -> dict:
    return {"route": perceive_step(runtime.context)}  # 409 / 422 nem tai day: endpoint chua mo response (prime)


async def reask_node(s: TurnGraphState, runtime: Runtime[TurnContext]) -> dict:
    reask_step(runtime.context)
    return {}


async def evaluate_node(s: TurnGraphState, runtime: Runtime[TurnContext]) -> dict:
    await evaluate_step(runtime.context)
    return {}


async def decide_node(s: TurnGraphState, runtime: Runtime[TurnContext]) -> dict:
    return {"route": decide_step(runtime.context)}


async def act_node(s: TurnGraphState, runtime: Runtime[TurnContext]) -> dict:
    act_step(runtime.context)
    return {}


async def ask_node(s: TurnGraphState, runtime: Runtime[TurnContext]) -> dict:
    """Interviewer dien dat cau hoi: moi event (meta / token / replace) day ra qua stream writer (stream_mode custom);
    finish_turn chay cuoi (trong turn_question_events) nen ket qua luot co cau hoi that truoc khi graph xong."""
    ctx, write = runtime.context, get_stream_writer()
    async with aclosing(turn_question_events(ctx.result, ctx.interviewer, ctx.collector)) as events:
        async for name, data in events:
            write((name, data))
    return {}


async def record_node(s: TurnGraphState, runtime: Runtime[TurnContext]) -> dict:
    """Luot xong (da hoi tiep hoac phien ket thuc): ghi state / transcript / last_turn vao checkpoint. Luot bi ngat
    giua `ask` khong toi day nen checkpoint giu state truoc luot: gui lai thi chay lai ca luot."""
    ctx = runtime.context
    return turn_values(s, ctx.req, ctx.result)
