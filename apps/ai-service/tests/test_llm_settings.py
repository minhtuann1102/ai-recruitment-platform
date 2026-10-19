import pytest

from app.llm.errors import ConfigError
from app.llm.settings import AGENTS, agent_settings, load_llm_settings

ENV = {"LLM_API_KEY": "test-key"}


def test_missing_key_raises():
    with pytest.raises(ConfigError):
        load_llm_settings({"LLM_API_KEY": "  "})


def test_defaults_and_flags():
    s = load_llm_settings(ENV)
    assert s.base_url == "https://openrouter.ai/api/v1" and s.default_model == "openai/gpt-4o-mini"
    assert s.embedding_dimensions == 1536 and s.structured_outputs is True and s.log_io is False
    s = load_llm_settings({**ENV, "LLM_STRUCTURED_OUTPUTS": "false", "LOG_LLM_IO": "true"})
    assert s.structured_outputs is False and s.log_io is True


def test_agent_table_matches_design():
    llm = load_llm_settings(ENV)
    ev = agent_settings("evaluator", llm, {})
    assert (ev.temperature, ev.max_tokens, ev.timeout_s, ev.seed, ev.retry_budget_s) == (0.0, 350, 8.0, 7, 10.0)
    iv = agent_settings("interviewer", llm, {})
    assert (iv.temperature, iv.max_tokens, iv.timeout_s) == (0.7, 200, 5.0)
    assert agent_settings("planner", llm, {}).max_tokens == 2500
    assert agent_settings("reporter", llm, {}).timeout_s == 60.0
    assert set(AGENTS) == {"cv_parser", "jd_parser", "planner", "evaluator", "interviewer", "reporter"}


def test_model_override_per_agent_only_affects_that_agent():
    llm = load_llm_settings(ENV)
    env = {"LLM_MODEL_EVALUATOR": "x/strong"}
    assert agent_settings("evaluator", llm, env).model == "x/strong"
    assert agent_settings("planner", llm, env).model == llm.default_model


def test_unknown_agent_rejected():
    with pytest.raises(ConfigError):
        agent_settings("nobody", load_llm_settings(ENV), {})
