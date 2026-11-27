"""SESSION_STORE: mac dinh memory; gia tri la / postgres thieu URL / pool sai -> ConfigError (khong khoi dong)."""
import pytest

from app.llm.errors import ConfigError
from app.session_store.session_store_settings import load_session_store_settings


def test_default_is_memory():
    s = load_session_store_settings({})
    assert s.kind == "memory" and s.db_url == "" and s.pool_max_size == 10


def test_postgres_reads_url_and_pool_size():
    s = load_session_store_settings({"SESSION_STORE": " Postgres ", "SESSION_DB_URL": "postgresql://x/y",
                                     "SESSION_DB_POOL_MAX": "4"})
    assert (s.kind, s.db_url, s.pool_max_size) == ("postgres", "postgresql://x/y", 4)


@pytest.mark.parametrize("env", [{"SESSION_STORE": "redis"}, {"SESSION_STORE": "postgres"},
                                 {"SESSION_DB_POOL_MAX": "0"}, {"SESSION_DB_POOL_MAX": "abc"}])
def test_bad_config_raises(env):
    with pytest.raises(ConfigError):
        load_session_store_settings(env)
