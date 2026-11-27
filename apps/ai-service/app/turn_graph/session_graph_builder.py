"""Dung graph ca phien (docs/ai-service/03, plan 261127-1517 phase 05):

START -> plan -> ask -> record -> wait_answer            (/start dung o interrupt cua wait_answer)
wait_answer -(answer)-> perceive -(reask)-> reask -> ask -> record -> wait_answer
perceive -(evaluate)-> evaluate -> decide -(follow_up | hint | ...)-> act -> ask
perceive / decide -(session_end)-> record -> wait_answer  (phien done: luot sau bi guard 409)
wait_answer -(finalize)-> report -> wait_answer           (report xong van cho: finalize goi lai duoc)

Vong ask -> ... -> ask la chu trinh Perceive-Evaluate-Decide-Act that; moi lan toi wait_answer graph dung bang
interrupt, /next-turn va /finalize resume bang Command(resume={"kind": ...}). Compile kem checkpointer chung.
"""
from functools import lru_cache

from langgraph.graph import START, StateGraph

from ..session_store.session_checkpointer import get_checkpointer
from ..turn_steps import SESSION_END
from .session_graph_nodes import (WAIT_ANSWER, act_node, ask_node, decide_node, evaluate_node, perceive_node,
                                  plan_node, record_node, reask_node, report_node, wait_answer_node)
from .session_run_context import SessionRunContext
from .turn_graph_builder import DECIDE_ACTIONS, route_of, mermaid_with_decide_labels
from .turn_graph_nodes import TurnGraphState


def build_session_graph(checkpointer=None):
    g = StateGraph(TurnGraphState, context_schema=SessionRunContext)
    for name, node in (("plan", plan_node), ("ask", ask_node), ("record", record_node),
                       (WAIT_ANSWER, wait_answer_node), ("perceive", perceive_node), ("reask", reask_node),
                       ("evaluate", evaluate_node), ("decide", decide_node), ("act", act_node),
                       ("report", report_node)):
        g.add_node(name, node)
    g.add_edge(START, "plan")
    g.add_edge("plan", "ask")
    g.add_edge("ask", "record")
    g.add_edge("record", WAIT_ANSWER)
    g.add_conditional_edges(WAIT_ANSWER, route_of, {"answer": "perceive", "finalize": "report"})
    g.add_conditional_edges("perceive", route_of, {SESSION_END: "record", "reask": "reask", "evaluate": "evaluate"})
    g.add_edge("reask", "ask")
    g.add_edge("evaluate", "decide")
    g.add_conditional_edges("decide", route_of, {SESSION_END: "record", **{a: "act" for a in DECIDE_ACTIONS}})
    g.add_edge("act", "ask")
    g.add_edge("report", WAIT_ANSWER)
    return g.compile(checkpointer=checkpointer)


@lru_cache(maxsize=4)
def _compiled(checkpointer):
    return build_session_graph(checkpointer)


def whole_session_graph():
    """Graph ca phien da compile voi checkpointer hien tai (compile mot lan moi checkpointer, nhu turn_graph)."""
    return _compiled(get_checkpointer())


def session_graph_mermaid() -> str:
    """Giong turn_graph_mermaid, bo canh wait_answer -> __end__ (LangGraph tu them vi nhanh re cua wait_answer khong
    liet ke het; phien khong bao gio ket thuc trong graph, luon cho o wait_answer)."""
    lines = [l for l in mermaid_with_decide_labels(whole_session_graph()).splitlines()
             if l.strip() != "wait_answer -.-> __end__;"]
    return "\n".join(lines) + "\n"
