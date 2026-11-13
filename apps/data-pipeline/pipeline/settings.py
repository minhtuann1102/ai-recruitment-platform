"""Cau hinh data pipeline doc tu bien moi truong (.env cua app khi chay local).

validate / process / crawl chay offline nen khong doi key khi import; chi index / search / eval
goi require_index_settings().
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent.parent
SEEDS_DIR = APP_DIR / "data" / "seeds" / "interview_qa"
GOLDEN_SET_PATH = APP_DIR / "data" / "seeds" / "golden_set.json"
PROCESSED_DIR = APP_DIR / "data" / "processed"
RAW_DIR = APP_DIR / "data" / "raw"
# Q&A crawl da dich + gan topic (lenh enrich); gitignore vi repo public (spec 005 Clarifications 2026-10-19)
ENRICHED_DIR = RAW_DIR / "enriched_qa"
# Phase B (spec 005 Session 2026-11-08): ket qua LLM cham lai topic / do kho / interview_style (lenh relabel)
RELABEL_DIR = RAW_DIR / "relabel"

# Spec 009 (JD): raw crawl + synthetic, JD chuan hoa, chunk, manifest seed deu nam ngoai git (FR-007);
# chi skill_dictionary.yaml la seed commit duoc
JD_RAW_DIR = RAW_DIR / "jd"
SKILL_DICTIONARY_PATH = APP_DIR / "data" / "seeds" / "skill_dictionary.yaml"
JD_NORMALIZED_PATH = PROCESSED_DIR / "jd_normalized.jsonl"
JD_CHUNKS_PATH = PROCESSED_DIR / "jd_chunks.jsonl"
JD_SEED_MANIFEST_PATH = PROCESSED_DIR / "job-seed-manifest.jsonl"

# Dau bo du lieu: chi don ban ghi cung dataset (FR-013)
CURATED_DATASET = "de_interview_qa"  # seed commit trong repo
CRAWLED_DATASET = "de_crawled_qa"  # crawl + dich, khong commit
SOURCE_TYPE = "interview_qa"

# Chi doc .env cua app, khong lan len .env goc cua monorepo
load_dotenv(APP_DIR / ".env")


class ConfigError(RuntimeError):
    pass


def canonical_embedding_model(name: str) -> str:
    """Ten luu vao knowledge_chunks.embedding_model: bo tien to provider (research R2).

    'openai/text-embedding-3-small' (OpenRouter) va 'text-embedding-3-small' (OpenAI) cung luu
    'text-embedding-3-small' de duong doc loc dung mot chuoi.
    """
    return name.strip().rsplit("/", 1)[-1]


def catalog_dir() -> Path:
    """Thu muc YAML topic catalog; duong dan tuong doi tinh tu thu muc app, khong tu cwd."""
    path = Path(os.getenv("CATALOG_DIR", "../ai-service/app/catalog"))
    return path if path.is_absolute() else (APP_DIR / path).resolve()


@dataclass(frozen=True)
class LlmSettings:
    api_key: str
    base_url: str
    llm_model: str


def require_llm_settings() -> LlmSettings:
    """Cau hinh cho enrich (dich + gan topic): chi can key LLM, khong can DB."""
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("thieu bien moi truong: LLM_API_KEY. Copy .env.example thanh .env va dien gia tri.")
    return LlmSettings(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        llm_model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
    )


@dataclass(frozen=True)
class RelabelSettings:
    api_key: str
    base_url: str
    model: str
    reasoning: str  # none | minimal | low | medium | high; "" = khong gui (model khong co reasoning)
    max_tokens: int  # gom ca token reasoning

    @property
    def openrouter(self) -> bool:
        return "openrouter.ai" in self.base_url


REASONING_LEVELS = ("", "none", "minimal", "low", "medium", "high")


def require_relabel_settings(model: str = "") -> RelabelSettings:
    """Cau hinh lenh relabel. Mac dinh dung key OpenAI cua embedding (EMBEDDING_API_KEY, api.openai.com) va
    gpt-6-luna; RELABEL_API_KEY / RELABEL_BASE_URL ghi de (vd OpenRouter). --model ghi de RELABEL_MODEL."""
    api_key = os.getenv("RELABEL_API_KEY", "").strip() or os.getenv("EMBEDDING_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("thieu bien moi truong: RELABEL_API_KEY hoac EMBEDDING_API_KEY (key OpenAI). Them vao .env.")
    reasoning = os.getenv("RELABEL_REASONING", "low").strip().lower()
    if reasoning not in REASONING_LEVELS:
        raise ConfigError(f"RELABEL_REASONING khong hop le: {reasoning} (chon {', '.join(REASONING_LEVELS[1:])})")
    base_url = (os.getenv("RELABEL_BASE_URL", "").strip() or os.getenv("EMBEDDING_BASE_URL", "").strip()
                or "https://api.openai.com/v1")
    return RelabelSettings(
        api_key=api_key,
        base_url=base_url,
        model=model.strip() or os.getenv("RELABEL_MODEL", "gpt-6-luna").strip(),
        reasoning=reasoning,
        max_tokens=int(os.getenv("RELABEL_MAX_TOKENS", "2000")),
    )


@dataclass(frozen=True)
class IndexSettings:
    api_key: str
    base_url: str
    embedding_model: str  # ten theo provider, dung khi goi API
    embedding_dimensions: int
    db_url: str

    @property
    def stored_model(self) -> str:
        return canonical_embedding_model(self.embedding_model)


def require_index_settings() -> IndexSettings:
    """Doc cau hinh cho index / search / eval; thieu key hoac DB thi bao loi ro (FR-019).

    Key embedding co the khac key LLM dich (vd DeepSeek de dich, OpenAI de embed): EMBEDDING_API_KEY /
    EMBEDDING_BASE_URL, khong dat thi dung LLM_API_KEY / LLM_BASE_URL.
    """
    api_key = (os.getenv("EMBEDDING_API_KEY", "").strip() or os.getenv("LLM_API_KEY", "").strip())
    db_url = os.getenv("AI_DB_URL", "").strip()
    missing = [name for name, value in (("EMBEDDING_API_KEY/LLM_API_KEY", api_key), ("AI_DB_URL", db_url)) if not value]
    if missing:
        raise ConfigError(
            f"thieu bien moi truong: {', '.join(missing)}. Copy .env.example thanh .env va dien gia tri."
        )
    return IndexSettings(
        api_key=api_key,
        base_url=os.getenv("EMBEDDING_BASE_URL", "").strip() or os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
        db_url=db_url,
    )
