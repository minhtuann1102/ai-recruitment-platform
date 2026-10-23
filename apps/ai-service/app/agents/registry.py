"""Chon cai dat `mock` hoac `llm` cho tung agent qua bien moi truong AGENT_<TEN>_MODE (mac dinh mock).

Mock giu lam fallback va cho CI khong can khoa API.
"""
import logging
import os
from typing import Any, Callable, Dict, Mapping, Optional

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


_llm_agents: Dict[str, Any] = {}
log = logging.getLogger("ai_service.agents")


def cached_llm_agent(agent: str, build: Callable[[Any], Any]) -> Optional[Any]:
    """Tao agent LLM mot lan voi gateway dung chung; loi cau hinh (vd thieu LLM_API_KEY) thi tra None de
    noi goi tu ve mock thay vi tra 500."""
    if agent not in _llm_agents:
        from ..llm.gateway import get_gateway  # import muon: registry khong phu thuoc gateway khi chi dung mock
        try:
            _llm_agents[agent] = build(get_gateway())
        except ConfigError as err:
            log.error("agent_config_error agent=%s error=%s", agent, err)
            return None
    return _llm_agents[agent]
