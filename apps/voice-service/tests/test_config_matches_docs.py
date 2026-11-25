"""Cau hinh khop tai lieu: bang "Cau hinh" cua data-model.md va .env.example liet ke dung cac bien ma config.py doc,
va mac dinh trong bang bang mac dinh cua Settings. Lech (them / doi mac dinh ma quen sua tai lieu) la test do."""
import re
from pathlib import Path

import pytest

from app.config import Settings

APP_DIR = Path(__file__).resolve().parents[1]
DATA_MODEL = APP_DIR.parents[1] / "specs" / "015-voice-mode" / "data-model.md"
ENV_EXAMPLE = APP_DIR / ".env.example"
# bien moi truong -> (truong Settings, cach doc gia tri trong bang)
FIELDS = {
    "BLAZE_API_KEY": ("blaze_api_key", str), "BLAZE_BASE_URL": ("blaze_base_url", str),
    "VOICE_SERVICE_INTERNAL_TOKEN": ("internal_token", str), "APP_ENV": ("app_env", str),
    "VOICE_STT_MODEL": ("stt_model", str), "VOICE_STT_REFINE": ("stt_refine", lambda v: v == "true"),
    "VOICE_TTS_MODEL": ("tts_model", str), "VOICE_TTS_VOICES": ("tts_voices", lambda v: tuple(x.strip() for x in v.split(","))),
    "VOICE_MAX_UPLOAD_MB": ("max_upload_mb", float), "VOICE_MAX_AUDIO_S": ("max_audio_s", float),
    "VOICE_MAX_TTS_CHARS": ("max_tts_chars", int), "VOICE_MAX_KEYWORDS": ("max_keywords", int),
    "VOICE_PROVIDER_TIMEOUT_S": ("provider_timeout_s", float), "VOICE_PROVIDER_RETRIES": ("provider_retries", int),
    "VOICE_PROVIDER_BACKOFF_S": ("provider_backoff_s", float), "VOICE_LONG_PAUSE_S": ("long_pause_s", float),
    "VOICE_FILLERS_SUPPORTED": ("fillers_supported", lambda v: v == "true"),
    "VOICE_FILLERS": ("fillers", lambda v: tuple(x.strip() for x in v.split(","))),
    "VOICE_RATE_SLOW_SPM": ("rate_slow_spm", float), "VOICE_RATE_FAST_SPM": ("rate_fast_spm", float),
    "VOICE_FILLER_NOTE_RATIO": ("filler_note_ratio", float), "VOICE_THINKING_NOTE_S": ("thinking_note_s", float),
}


def documented_defaults() -> dict:
    """{bien: gia tri mac dinh o dang chuoi, hoac '—'} tu bang trong data-model.md."""
    rows = re.findall(r"^\| `([A-Z_]+)` \| (.+?) \|", DATA_MODEL.read_text(encoding="utf-8"), flags=re.M)
    return {name: default.strip("` ") for name, default in rows}


def env_vars_read_by_config() -> set:
    source = (APP_DIR / "app" / "config.py").read_text(encoding="utf-8")
    return set(re.findall(r'"((?:VOICE_|BLAZE_)[A-Z_]+|APP_ENV)"', source))


def test_data_model_table_lists_exactly_the_variables_config_reads():
    assert set(documented_defaults()) == env_vars_read_by_config() == set(FIELDS)


def test_env_example_lists_every_variable():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [name for name in FIELDS if not re.search(rf"^#?\s*{name}=", text, flags=re.M)]
    assert missing == []


@pytest.mark.parametrize("name", sorted(FIELDS))
def test_default_in_data_model_table_equals_settings_default(name):
    field, cast = FIELDS[name]
    documented = documented_defaults()[name]
    expected = "" if documented == "—" else cast(documented)
    assert getattr(Settings(), field) == expected


def test_values_in_env_example_that_are_set_equal_defaults():
    """Gia tri mau trong .env.example (dong khong comment, co gia tri) khong lech mac dinh."""
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z_]+)=(.+)$", line)
        if match and match.group(1) in FIELDS:
            field, cast = FIELDS[match.group(1)]
            assert getattr(Settings(), field) == cast(match.group(2).strip()), match.group(1)
