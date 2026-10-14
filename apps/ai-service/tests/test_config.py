import pytest

from app.config import ConfigError, load_settings


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr("app.config.os.getenv", lambda k, d=None: {"LLM_API_KEY": ""}.get(k, d))
    with pytest.raises(ConfigError):
        load_settings()


def test_defaults_and_overrides(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "x/y")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    s = load_settings()
    assert s.llm_model == "x/y"
    assert s.base_url == "https://openrouter.ai/api/v1"
    assert s.embedding_dimensions == 1536
