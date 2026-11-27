"""Chon graph cua phien theo SESSION_GRAPH: per_turn (phase 02, mac dinh) hoac session (graph ca phien, phase 05).

Moi noi doc / ghi thread phien (guard, record, seed test, /start) phai dung cung mot graph, vi aget_state tinh `next`
theo dung graph da ghi thread: dung ham nay thay vi turn_graph() truc tiep.
"""
from ..session_store.session_graph_settings import session_graph_enabled
from .session_graph_builder import whole_session_graph
from .turn_graph_builder import turn_graph


def session_graph():
    return whole_session_graph() if session_graph_enabled() else turn_graph()
