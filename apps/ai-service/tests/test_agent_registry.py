import pytest

from app.agents.registry import AgentRegistry, agent_mode
from app.llm.errors import ConfigError


def test_default_mode_is_mock():
    assert agent_mode("evaluator", {}) == "mock"


def test_mode_from_env_and_invalid_values():
    assert agent_mode("evaluator", {"AGENT_EVALUATOR_MODE": "LLM"}) == "llm"
    with pytest.raises(ConfigError):
        agent_mode("evaluator", {"AGENT_EVALUATOR_MODE": "magic"})
    with pytest.raises(ConfigError):
        agent_mode("nobody", {})


def test_resolve_picks_implementation_by_mode():
    reg = AgentRegistry({"AGENT_PLANNER_MODE": "llm"})
    reg.register("planner", mock="M", llm="L")
    reg.register("evaluator", mock="M2", llm="L2")
    assert reg.resolve("planner") == "L" and reg.resolve("evaluator") == "M2"


def test_llm_mode_without_implementation_fails_loudly():
    reg = AgentRegistry({"AGENT_PLANNER_MODE": "llm"})
    reg.register("planner", mock="M")
    with pytest.raises(ConfigError):
        reg.resolve("planner")
    with pytest.raises(ConfigError):
        reg.resolve("reporter")  # chua dang ky
