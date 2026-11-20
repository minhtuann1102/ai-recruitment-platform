"""Ghi chu agent (phase 07): provider chon prompt v11 co dinh ca phien, v8 / v9 / v10 giu nguyen khi cong tat, canh bao lech."""
import app.agents.evaluator_provider as provider
from tests.test_replan_v10_prompt import llm_mode  # noqa: F401  (fixture)


def test_provider_picks_v11_only_for_hybrid_plus_notes_and_pins_the_rest(llm_mode, monkeypatch):
    for k in ("POLICY_MODE", "REPLAN_ENABLED", "AGENT_NOTES_ENABLED"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("AGENT_NOTES_ENABLED", "true")
    assert provider.get_evaluator().prompt_version == "v8"  # rules: co notes khong doi prompt
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    first = provider.get_evaluator()
    assert first.prompt_version == "v11" and provider.get_evaluator() is first
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    assert provider.get_evaluator().prompt_version == "v11"  # v11 gom ca swap
    monkeypatch.setenv("AGENT_NOTES_ENABLED", "false")
    assert provider.get_evaluator().prompt_version == "v10"
    monkeypatch.delenv("REPLAN_ENABLED")
    assert provider.get_evaluator().prompt_version == "v9"
    monkeypatch.delenv("POLICY_MODE")
    assert provider.get_evaluator().prompt_version == "v8"


def test_notes_with_an_older_prompt_override_warn_once(llm_mode, monkeypatch, caplog):
    caplog.set_level("WARNING", logger="ai_service.evaluator")
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("AGENT_NOTES_ENABLED", "true")
    monkeypatch.setenv("EVALUATOR_PROMPT_VERSION", "v9")
    provider.get_evaluator()
    provider.get_evaluator()
    assert sum("AGENT_NOTES_ENABLED" in r.message for r in caplog.records) == 1


def test_forcing_v11_while_the_flag_is_off_warns_once(llm_mode, monkeypatch, caplog):
    caplog.set_level("WARNING", logger="ai_service.evaluator")
    monkeypatch.delenv("AGENT_NOTES_ENABLED", raising=False)
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("EVALUATOR_PROMPT_VERSION", "v11")
    provider.get_evaluator()
    provider.get_evaluator()
    assert sum("AGENT_NOTES_ENABLED tat" in r.message for r in caplog.records) == 1
