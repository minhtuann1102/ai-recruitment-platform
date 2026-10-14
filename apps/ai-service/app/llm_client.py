"""Client OpenAI-compatible dung chung (OpenRouter hoac OpenAI), khong gan cung nha cung cap."""
from openai import OpenAI

from .config import Settings, load_settings


def build_client(settings: Settings) -> OpenAI:
    return OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
        max_retries=2,
    )


def get_client_and_settings():
    settings = load_settings()
    return build_client(settings), settings
