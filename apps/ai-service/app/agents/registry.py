"""Chon cai dat `mock` hoac `llm` cho tung agent qua bien moi truong AGENT_<TEN>_MODE (mac dinh mock).

Mock giu lam fallback va cho CI khong can khoa API.
"""
import os
from typing import Any, Dict, Mapping, Optional

from ..llm.errors import ConfigError
from ..llm.settings import AGENTS

MODES = ("mock", "llm")


def agent_mode(agent: str, env: Optional[Mapping[str, str]] = None) -> str:
    if agent not in AGENTS:
        raise ConfigError(f"agent khong hop le: {agent}")
    env = os.environ if env is None else env
    mode = (env.get(f"AGENT_{agent.upper()}_MODE") or "mock").strip().lower()
    if mode not in MODES:
        raise ConfigError(f"AGENT_{agent.upper()}_MODE phai la mock hoac llm, nhan '{mode}'")
    return mode


class AgentRegistry:
    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self._env = env
        self._impl: Dict[str, Dict[str, Any]] = {}

    def register(self, agent: str, *, mock: Any, llm: Any = None) -> None:
        if agent not in AGENTS:
            raise ConfigError(f"agent khong hop le: {agent}")
        self._impl[agent] = {"mock": mock, "llm": llm}

    def resolve(self, agent: str) -> Any:
        mode = agent_mode(agent, self._env)
        impls = self._impl.get(agent)
        if impls is None:
            raise ConfigError(f"agent '{agent}' chua duoc dang ky")
        if impls[mode] is None:
            raise ConfigError(f"agent '{agent}' chua co cai dat che do '{mode}'")
        return impls[mode]
