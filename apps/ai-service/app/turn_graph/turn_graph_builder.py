"""Dung graph mot luot next-turn (docs/ai-service/03, doc 12 muc 3 + G5):

perceive -(reask)-> reask -> ask -> END
perceive -(evaluate)-> evaluate -> decide -(follow_up | hint | clarify | next_topic | next_phase | wrap_up)-> act -> ask
perceive / decide -(session_end)-> END (phien ket thuc: wrap-up da tra loi, qua han cung)

Canh cua decide ghi tung hanh dong de so do Mermaid hien du nhanh nhu state machine o doc 03.
"""
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from ..turn_steps import SESSION_END
from .turn_graph_nodes import (TurnGraphState, act_node, ask_node, decide_node, evaluate_node, perceive_node,
                               reask_node)

# moi hanh dong decide_step co the tra (Decision.action, ca forced / low_performance); hanh dong ngoai danh sach
# thi LangGraph bao loi (KeyError -> 500) - tests/test_turn_graph.py kiem moi nguon hanh dong deu nam trong day
DECIDE_ACTIONS = ("follow_up", "hint", "clarify", "next_topic", "next_phase", "wrap_up")


def _route(s: TurnGraphState) -> str:
    return s["route"]


def build_turn_graph():
    g = StateGraph(TurnGraphState)
    for name, node in (("perceive", perceive_node), ("reask", reask_node), ("evaluate", evaluate_node),
                       ("decide", decide_node), ("act", act_node), ("ask", ask_node)):
        g.add_node(name, node)
    g.add_edge(START, "perceive")
    g.add_conditional_edges("perceive", _route, {SESSION_END: END, "reask": "reask", "evaluate": "evaluate"})
    g.add_edge("reask", "ask")
    g.add_edge("evaluate", "decide")
    g.add_conditional_edges("decide", _route, {SESSION_END: END, **{a: "act" for a in DECIDE_ACTIONS}})
    g.add_edge("act", "ask")
    g.add_edge("ask", END)
    return g.compile()  # pha A: khong checkpointer


@lru_cache(maxsize=1)
def turn_graph():
    """Graph da compile, dung chung moi request (compile mot lan)."""
    return build_turn_graph()


def turn_graph_mermaid() -> str:
    """So do Mermaid cho docs / bao cao. draw_mermaid() gop cac canh cung dich (decide -> act) thanh mot canh mang
    nhan cuoi cung; ghi lai du danh sach hanh dong tren canh do."""
    labels = ", ".join(DECIDE_ACTIONS)  # khong dung "|": ky tu nhan canh cua Mermaid
    lines = []
    for line in turn_graph().get_graph().draw_mermaid().splitlines():
        if line.strip().startswith("decide -.") and line.rstrip().endswith("-> act;"):
            line = f"\tdecide -. &nbsp;{labels}&nbsp; .-> act;"
        lines.append(line)
    return "\n".join(lines) + "\n"
