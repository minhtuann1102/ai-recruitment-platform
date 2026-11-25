"""Cau hinh voice-service doc tu bien moi truong (data-model.md muc "Cau hinh").

Nap `apps/voice-service/.env` khi import (nhu apps/data-pipeline/pipeline/settings.py): bien moi truong that ghi de file.
`Settings` la dataclass bat bien co gia tri mac dinh day du: test dung `Settings(...)` truc tiep, khong doc os.environ.
Gia tri sai (so <= 0, danh sach giong rong...) lam service khong khoi dong (ConfigError).
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent.parent
# Chi doc .env cua app, khong lan len .env goc cua monorepo
load_dotenv(APP_DIR / ".env")

# tu dem mac dinh (research R5); "a" dung mot minh khong tinh. Ghi de bang VOICE_FILLERS (phan cach dau phay)
DEFAULT_FILLERS: Tuple[str, ...] = ("ừm", "ừ", "ờ", "à", "ơ", "kiểu như", "thì là", "nói chung là")
STRICT_ENVS = frozenset({"staging", "production", "prod"})


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    # nha cung cap Blaze (key chi doc tu env phia server, FR-016)
    blaze_api_key: str = ""
    blaze_base_url: str = "https://api.blaze.vn"
    stt_model: str = "blaze-stt-1.5"
    stt_refine: bool = False
    tts_model: str = "blaze-tts-1.5-realtime"
    tts_voices: Tuple[str, ...] = ("HN-Nam-2-BL",)  # phan tu dau la giong mac dinh
    tts_speed: float = 1.0  # chi gui len Blaze khi khac 1.0 (spike chi xac nhan model/input/voice/response_format)
    tts_stream_format: str = ""  # vd "audio"; rong = khong gui (spike chua xac nhan tham so nay)
    # bao mat
    internal_token: str = ""
    app_env: str = "dev"
    # gioi han dau vao
    max_upload_mb: float = 10
    max_audio_s: float = 300
    max_tts_chars: int = 1000
    max_keywords: int = 100
    # goi nha cung cap
    provider_timeout_s: float = 60  # spike 2026-11-25: STT ~5 s + 0.15 x do dai audio; cung la `timeout` cua STT
    provider_retries: int = 2
    provider_backoff_s: float = 0.5  # co so backoff: lan thu n cho backoff * 2^n
    parallel_provider_calls: bool = False  # goi VAD + STT song song (goi Starter chi 1 luong: mac dinh tuan tu)
    # chi so trinh bay
    long_pause_s: float = 2.0
    fillers_supported: bool = True
    fillers: Tuple[str, ...] = DEFAULT_FILLERS
    # nguong sinh nhan xet cuoi phien (data-model.md)
    rate_slow_spm: float = 100
    rate_fast_spm: float = 200
    filler_note_ratio: float = 0.05
    thinking_note_s: float = 10

    def __post_init__(self) -> None:
        positives = {"max_upload_mb": self.max_upload_mb, "max_audio_s": self.max_audio_s,
                     "max_tts_chars": self.max_tts_chars, "max_keywords": self.max_keywords,
                     "provider_timeout_s": self.provider_timeout_s, "long_pause_s": self.long_pause_s,
                     "tts_speed": self.tts_speed, "rate_slow_spm": self.rate_slow_spm,
                     "rate_fast_spm": self.rate_fast_spm, "filler_note_ratio": self.filler_note_ratio,
                     "thinking_note_s": self.thinking_note_s}
        bad = [name for name, value in positives.items() if not value > 0]
        if self.provider_retries < 0 or self.provider_backoff_s < 0:
            bad += [n for n, v in (("provider_retries", self.provider_retries),
                                   ("provider_backoff_s", self.provider_backoff_s)) if v < 0]
        if not self.tts_voices:
            bad.append("tts_voices")
        if bad:
            raise ConfigError(f"cau hinh khong hop le (can so > 0, danh sach giong khong rong): {', '.join(bad)}")

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def strict_env(self) -> bool:
        return self.app_env.lower() in STRICT_ENVS

    @property
    def default_voice(self) -> str:
        return self.tts_voices[0]


def _num(env: Mapping[str, str], name: str, cast, default):
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ConfigError(f"{name} khong phai so hop le: {raw!r}") from None


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name, "").strip().lower()
    if not raw:
        return default
    if raw not in ("true", "false"):
        raise ConfigError(f"{name} chi nhan true / false, nhan {raw!r}")
    return raw == "true"


def _csv(env: Mapping[str, str], name: str, default: Tuple[str, ...]) -> Tuple[str, ...]:
    items = tuple(p.strip() for p in env.get(name, "").split(",") if p.strip())
    return items or default


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    """Doc Settings tu `env` (mac dinh os.environ). Bien vang hoac rong thi dung mac dinh."""
    env = os.environ if env is None else env
    d = Settings()  # mac dinh nam o mot cho: dataclass
    return Settings(
        blaze_api_key=env.get("BLAZE_API_KEY", "").strip(),
        blaze_base_url=(env.get("BLAZE_BASE_URL", "").strip() or d.blaze_base_url).rstrip("/"),
        stt_model=env.get("VOICE_STT_MODEL", "").strip() or d.stt_model,
        stt_refine=_flag(env, "VOICE_STT_REFINE", d.stt_refine),
        tts_model=env.get("VOICE_TTS_MODEL", "").strip() or d.tts_model,
        tts_voices=_csv(env, "VOICE_TTS_VOICES", d.tts_voices),
        tts_speed=_num(env, "VOICE_TTS_SPEED", float, d.tts_speed),
        tts_stream_format=env.get("VOICE_TTS_STREAM_FORMAT", "").strip(),
        internal_token=env.get("VOICE_SERVICE_INTERNAL_TOKEN", "").strip(),
        app_env=env.get("APP_ENV", "").strip() or d.app_env,
        max_upload_mb=_num(env, "VOICE_MAX_UPLOAD_MB", float, d.max_upload_mb),
        max_audio_s=_num(env, "VOICE_MAX_AUDIO_S", float, d.max_audio_s),
        max_tts_chars=_num(env, "VOICE_MAX_TTS_CHARS", int, d.max_tts_chars),
        max_keywords=_num(env, "VOICE_MAX_KEYWORDS", int, d.max_keywords),
        provider_timeout_s=_num(env, "VOICE_PROVIDER_TIMEOUT_S", float, d.provider_timeout_s),
        provider_retries=_num(env, "VOICE_PROVIDER_RETRIES", int, d.provider_retries),
        provider_backoff_s=_num(env, "VOICE_PROVIDER_BACKOFF_S", float, d.provider_backoff_s),
        parallel_provider_calls=_flag(env, "VOICE_PARALLEL_PROVIDER_CALLS", d.parallel_provider_calls),
        long_pause_s=_num(env, "VOICE_LONG_PAUSE_S", float, d.long_pause_s),
        fillers_supported=_flag(env, "VOICE_FILLERS_SUPPORTED", d.fillers_supported),
        fillers=_csv(env, "VOICE_FILLERS", d.fillers),
        rate_slow_spm=_num(env, "VOICE_RATE_SLOW_SPM", float, d.rate_slow_spm),
        rate_fast_spm=_num(env, "VOICE_RATE_FAST_SPM", float, d.rate_fast_spm),
        filler_note_ratio=_num(env, "VOICE_FILLER_NOTE_RATIO", float, d.filler_note_ratio),
        thinking_note_s=_num(env, "VOICE_THINKING_NOTE_S", float, d.thinking_note_s),
    )
