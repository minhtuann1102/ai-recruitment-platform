"""Cau hinh noi luu phien tu bien moi truong: SESSION_STORE=memory|postgres (mac dinh memory)."""
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from dotenv import load_dotenv

from ..llm.errors import ConfigError

load_dotenv()
KINDS = ("memory", "postgres")


@dataclass(frozen=True)
class SessionStoreSettings:
    kind: str  # memory: mat khi restart, chi mot instance (compose mock, test, dev-play); postgres: SESSION_DB_URL
    db_url: str = ""
    pool_max_size: int = 10


def _positive_int(env: Mapping[str, str], name: str, default: str) -> int:
    raw = env.get(name) or default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value <= 0:
        raise ConfigError(f"{name} phai la so nguyen duong, nhan '{raw}'")
    return value


def load_session_store_settings(env: Optional[Mapping[str, str]] = None) -> SessionStoreSettings:
    env = os.environ if env is None else env
    kind = (env.get("SESSION_STORE") or "memory").strip().lower()
    if kind not in KINDS:
        raise ConfigError(f"SESSION_STORE phai la memory hoac postgres, nhan '{kind}'")
    db_url = (env.get("SESSION_DB_URL") or "").strip()
    if kind == "postgres" and not db_url:
        raise ConfigError("SESSION_STORE=postgres nhung SESSION_DB_URL chua duoc dat")
    return SessionStoreSettings(kind, db_url, _positive_int(env, "SESSION_DB_POOL_MAX", "10"))
