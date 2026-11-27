"""Dung graph mot luot next-turn (docs/ai-service/03, doc 12 muc 3 + G5):

perceive -(reask)-> reask -> ask -> record -> END
perceive -(evaluate)-> evaluate -> decide -(follow_up | hint | clarify | next_topic | next_phase | wrap_up)-> act -> ask
perceive / decide -(session_end)-> record (phien ket thuc: wrap-up da tra loi, qua han cung)

Canh cua decide ghi tung hanh dong de so do Mermaid hien du nhanh nhu state machine o doc 03. Compile kem checkpointer
cua app/session_store (phase 03); endpoint chay voi durability="exit": moi luot ghi mot checkpoint khi graph xong.
"""
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from ..session_store.session_checkpointer import get_checkpointer
from ..turn_steps import SESSION_END, TurnContext
from .turn_graph_nodes import (TurnGraphState, act_node, ask_node, decide_node, evaluate_node, perceive_node,
                               reask_node, record_node)

# moi hanh dong decide_step co the tra (Decision.action, ca forced / low_performance); hanh dong ngoai danh sach
# thi LangGraph bao loi (KeyError -> 500) - tests/test_turn_graph.py kiem moi nguon hanh dong deu nam trong day
DECIDE_ACTIONS = ("follow_up", "hint", "clarify", "next_topic", "next_phase", "wrap_up")


def route_of(s: TurnGraphState) -> str:
    return s["route"]


def build_turn_graph(checkpointer=None):
    g = StateGraph(TurnGraphState, context_schema=TurnContext)
    for name, node in (("perceive", perceive_node), ("reask", reask_node), ("evaluate", evaluate_node),
                       ("decide", decide_node), ("act", act_node), ("ask", ask_node), ("record", record_node)):
        g.add_node(name, node)
    g.add_edge(START, "perceive")
    g.add_conditional_edges("perceive", route_of, {SESSION_END: "record", "reask": "reask", "evaluate": "evaluate"})
    g.add_edge("reask", "ask")
    g.add_edge("evaluate", "decide")
    g.add_conditional_edges("decide", route_of, {SESSION_END: "record", **{a: "act" for a in DECIDE_ACTIONS}})
    g.add_edge("act", "ask")
    g.add_edge("ask", "record")
    g.add_edge("record", END)
    return g.compile(checkpointer=checkpointer)


@lru_cache(maxsize=4)
def _compiled(checkpointer):
    return build_turn_graph(checkpointer)


def turn_graph():
    """Graph da compile voi checkpointer hien tai, dung chung moi request (compile mot lan moi checkpointer: test
    doi InMemorySaver moi thi graph compile lai)."""
    return _compiled(get_checkpointer())


def mermaid_with_decide_labels(graph) -> str:
    """So do Mermaid cho docs / bao cao. draw_mermaid() gop cac canh cung dich (decide -> act) thanh mot canh mang
    nhan cuoi cung; ghi lai du danh sach hanh dong tren canh do."""
    labels = ", ".join(DECIDE_ACTIONS)  # khong dung "|": ky tu nhan canh cua Mermaid
    lines = []
    for line in graph.get_graph().draw_mermaid().splitlines():
        if line.strip().startswith("decide -.") and line.rstrip().endswith("-> act;"):
            line = f"\tdecide -. &nbsp;{labels}&nbsp; .-> act;"
        lines.append(line)
    return "\n".join(lines) + "\n"


def turn_graph_mermaid() -> str:
    return mermaid_with_decide_labels(turn_graph())
