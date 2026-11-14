"""Chon cai dat `mock` hoac `llm` cho tung agent qua bien moi truong AGENT_<TEN>_MODE (mac dinh mock).

Mock giu lam fallback va cho CI khong can khoa API.
"""
import logging
import os
from typing import Any, Callable, Dict, Mapping, Optional

from ..llm.errors import ConfigError
from ..llm.settings import AGENTS, load_llm_settings
from ..llm.usage import CallRecord, UsageCollector
from ..prompts.store import PromptStore
from ..security import STRICT_ENVS
from .evaluator import DEFAULT_PROMPT_VERSION

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


def _llm_config_error(agent: str, env: Mapping[str, str]) -> Optional[Exception]:
    """Dieu kien de agent chay LLM that, kiem re (khong goi mang) de health va luc khoi dong cung dung duoc."""
    try:
        load_llm_settings(env)
        if agent == "evaluator":  # EVALUATOR_PROMPT_VERSION go sai cung lam Evaluator ve mock (evaluator_provider.py)
            PromptStore().get(agent, env.get("EVALUATOR_PROMPT_VERSION") or DEFAULT_PROMPT_VERSION)
    except (ConfigError, FileNotFoundError, ValueError) as err:
        return err
    return None


def agent_status(env: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """Che do thuc te tung agent: mock | llm | config_error. config_error: thieu khoa / prompt thi agent chay mock;
    AGENT_*_MODE sai hoac gia tri env sai dinh dang thi request dung agent do tra 500 (may dev, check_agent_config)."""
    env = os.environ if env is None else env
    status = {}
    for agent in AGENTS:
        try:
            mode = agent_mode(agent, env)
        except ConfigError:
            mode = "config_error"
        status[agent] = "config_error" if mode == "llm" and _llm_config_error(agent, env) else mode
    return status


def check_agent_config(env: Optional[Mapping[str, str]] = None) -> None:
    """Goi luc khoi dong. Staging/production (APP_ENV) thieu cau hinh thi dung han thay vi cham diem bang mock;
    may dev van chay tiep, co log, /api/health va metadata.fallbacks bao."""
    env = os.environ if env is None else env
    status = agent_status(env)
    broken = [a for a, s in status.items() if s == "config_error"]
    strict = env.get("APP_ENV", "dev").lower() in STRICT_ENVS
    if broken and strict:
        raise ConfigError(f"agent thieu cau hinh LLM: {', '.join(broken)}")
    if broken:
        log.error("agent_config_error agents=%s", ",".join(broken))
    mocked = [a for a, s in status.items() if s == "mock"]
    if strict and mocked:  # co the la chu y (staging de FSD tich hop) nen chi canh bao
        log.warning("agent_mock_in_strict_env agents=%s", ",".join(mocked))


def config_fallback(agent: str) -> str:
    return f"{agent}_config_error"


def record_config_fallback(agent: str, collector: Optional[UsageCollector]) -> None:
    if collector is not None:
        collector.add(CallRecord(agent, "mock", fallback=config_fallback(agent)))


def cached_llm_agent(agent: str, build: Callable[[Any], Any]) -> Optional[Any]:
    """Tao agent LLM mot lan voi gateway dung chung; loi cau hinh (vd thieu LLM_API_KEY) thi tra None de
    noi goi tu ve mock thay vi tra 500; noi goi ghi fallback <agent>_config_error de response khong im lang."""
    if agent not in _llm_agents:
        from ..llm.gateway import get_gateway  # import muon: registry khong phu thuoc gateway khi chi dung mock
        try:
            _llm_agents[agent] = build(get_gateway())
        except ConfigError as err:
            log.error("agent_config_error agent=%s error=%s", agent, err)
            return None
    return _llm_agents[agent]
