"""017 US2 T014: cau hinh MATCH_*; sai trong so -> ConfigError; mock khong can AI_DB_URL / LLM_API_KEY."""
import logging

import pytest

from app.llm.errors import ConfigError
from app.matching.settings import MatchWeights, load_match_settings


def test_defaults_match_the_contract_table():
    s = load_match_settings({})
    assert s.mock is False
    assert s.weights == MatchWeights(0.6, 0.3, 0.1)
    assert (s.max_level_gap, s.max_results, s.index_refresh_s, s.embed_timeout_s) == (1, 50, 300, 5.0)
    assert s.embedding_model == "text-embedding-3-small" and s.connect_timeout_s == 3 and s.db_url == ""


def test_mock_needs_no_db_url_and_no_llm_key():
    s = load_match_settings({"MATCH_MOCK": "true"})  # env rong: khong AI_DB_URL, khong LLM_API_KEY
    assert s.mock is True and s.db_url == ""


def test_missing_db_url_does_not_raise_even_without_mock_and_ignores_rag_enabled():
    # loi chi lo ra luc nap chi muc (503 match_index_unavailable), khong chan khoi dong app
    assert load_match_settings({"RAG_ENABLED": "true"}).db_url == ""
    assert load_match_settings({"RAG_ENABLED": "false", "AI_DB_URL": "postgresql://x"}).db_url == "postgresql://x"


def test_overrides_and_stored_model_name():
    s = load_match_settings({
        "MATCH_WEIGHTS": "0.5, 0.25 ,0.25", "MATCH_MAX_LEVEL_GAP": "0", "MATCH_MAX_RESULTS": "20",
        "MATCH_INDEX_REFRESH_S": "60", "MATCH_EMBED_TIMEOUT_S": "2.5", "AI_DB_CONNECT_TIMEOUT_S": "7",
        "EMBEDDING_MODEL": "openai/text-embedding-3-large",
    })
    assert s.weights == MatchWeights(0.5, 0.25, 0.25)
    assert (s.max_level_gap, s.max_results, s.index_refresh_s, s.embed_timeout_s) == (0, 20, 60, 2.5)
    assert s.connect_timeout_s == 7 and s.embedding_model == "text-embedding-3-large"  # bo tien to provider


@pytest.mark.parametrize("raw", [
    "0.6,0.3,0.2",  # tong 1.1
    "0.5,0.3,0.1",  # tong 0.9
    "0.7,0.5,-0.2",  # am du tong bang 1
    "0.6,0.4",  # thieu phan tu
    "0.6,0.2,0.1,0.1",  # thua phan tu
    "a,b,c", "0.6;0.3;0.1",  # sai dinh dang
    "nan,0.5,0.5", "inf,0,0", "0.6,0.3,nan",  # nan / inf lot qua so sanh thuong
])
def test_bad_weights_raise_config_error(raw):
    with pytest.raises(ConfigError, match="MATCH_WEIGHTS"):
        load_match_settings({"MATCH_WEIGHTS": raw})


def test_blank_weights_use_the_default():
    assert load_match_settings({"MATCH_WEIGHTS": "  "}).weights == MatchWeights(0.6, 0.3, 0.1)


def test_weights_sum_tolerance_is_1e_minus_6():
    load_match_settings({"MATCH_WEIGHTS": "0.6,0.3,0.1000005"})  # lech 5e-7: nhan
    with pytest.raises(ConfigError):
        load_match_settings({"MATCH_WEIGHTS": "0.6,0.3,0.100002"})  # lech 2e-6: tu choi


@pytest.mark.parametrize("name,value", [
    ("MATCH_MAX_LEVEL_GAP", "-1"), ("MATCH_MAX_LEVEL_GAP", "x"), ("MATCH_MAX_RESULTS", "0"),
    ("MATCH_INDEX_REFRESH_S", "0"), ("MATCH_EMBED_TIMEOUT_S", "0"), ("MATCH_EMBED_TIMEOUT_S", "nan"),
])
def test_bad_numeric_settings_raise_config_error(name, value):
    with pytest.raises(ConfigError, match=name):
        load_match_settings({name: value})


@pytest.mark.parametrize("value", ["0", "-1", "3.5", "abc"])
def test_bad_shared_db_timeout_falls_back_to_the_default_instead_of_stopping_startup(value, caplog):
    # AI_DB_CONNECT_TIMEOUT_S la bien cua RAG (RAG xu ly mem): chi MATCH_* sai moi duoc chan khoi dong
    with caplog.at_level(logging.WARNING, logger="ai_service.matching"):
        s = load_match_settings({"AI_DB_CONNECT_TIMEOUT_S": value})
    assert s.connect_timeout_s == 3
    assert "match_config_fallback var=AI_DB_CONNECT_TIMEOUT_S default=3" in caplog.text


def test_valid_shared_db_timeout_is_used_without_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="ai_service.matching"):
        assert load_match_settings({"AI_DB_CONNECT_TIMEOUT_S": "10"}).connect_timeout_s == 10
    assert caplog.text == ""
