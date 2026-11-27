"""Cau hinh graph phien theo SESSION_GRAPH=per_turn|session (mac dinh per_turn, plan 261127-1517 phase 05).

per_turn: moi luot chay mot graph ngan (phase 02), thread cua phien do endpoint noi tiep bang record.
session: mot graph cho ca phien, cho tra loi bang `interrupt` o node `wait_answer`; /next-turn va /finalize resume.
Gia tri sai -> ConfigError luc khoi dong (giong SESSION_STORE). Doc moi lan goi de test doi gia tri duoc.
"""
import os
from typing import Mapping, Optional

from ..llm.errors import ConfigError

MODES = ("per_turn", "session")


def load_session_graph_mode(env: Optional[Mapping[str, str]] = None) -> str:
    env = os.environ if env is None else env
    mode = (env.get("SESSION_GRAPH") or "per_turn").strip().lower()
    if mode not in MODES:
        raise ConfigError(f"SESSION_GRAPH phai la per_turn hoac session, nhan '{mode}'")
    return mode


def session_graph_enabled() -> bool:
    return load_session_graph_mode() == "session"
