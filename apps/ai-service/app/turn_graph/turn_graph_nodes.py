"""Node cua graph mot luot: moi node goi dung mot buoc cua app/turn_steps (Perceive / Evaluate / Decide / Act) hoac
stream cau hoi (node `ask`). State graph chi co `ctx` (TurnContext cua luot) va `route` (canh tiep theo).

Pha A (plan 261127-1517): khong checkpointer, ctx la object cua request. Pha B tach plan / state thanh key rieng de
luu (doc 12, G6). Moi node la async: tranh LangGraph day ham sync sang thread pool.
"""
from contextlib import aclosing
from typing import TypedDict

from langgraph.config import get_stream_writer

from ..question_stream import turn_question_events
from ..turn_steps import TurnContext, act_step, decide_step, evaluate_step, perceive_step, reask_step


class TurnGraphState(TypedDict, total=False):
    ctx: TurnContext
    route: str  # perceive: session_end | reask | evaluate; decide: session_end | follow_up | hint | next_topic | ...


async def perceive_node(s: TurnGraphState) -> dict:
    return {"route": perceive_step(s["ctx"])}  # 409 / 422 nem tai day: endpoint chua mo response (runner.prime)


async def reask_node(s: TurnGraphState) -> dict:
    reask_step(s["ctx"])
    return {}


async def evaluate_node(s: TurnGraphState) -> dict:
    await evaluate_step(s["ctx"])
    return {}


async def decide_node(s: TurnGraphState) -> dict:
    return {"route": decide_step(s["ctx"])}


async def act_node(s: TurnGraphState) -> dict:
    act_step(s["ctx"])
    return {}


async def ask_node(s: TurnGraphState) -> dict:
    """Interviewer dien dat cau hoi: moi event (meta / token / replace) day ra qua stream writer (stream_mode custom);
    finish_turn chay cuoi (trong turn_question_events) nen ket qua luot co cau hoi that truoc khi graph xong."""
    ctx, write = s["ctx"], get_stream_writer()
    async with aclosing(turn_question_events(ctx.result, ctx.interviewer, ctx.collector)) as events:
        async for name, data in events:
            write((name, data))
    return {}
