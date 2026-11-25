"""audio_validation (T016) va config (T006): kiem tep, moc thoi gian client, mac dinh va gia tri sai cua cau hinh."""
import pytest
from starlette.formparsers import MultiPartParser

from app.api_error import ApiError
from app.audio_validation import keep_uploads_in_memory, parse_client_time, reject_oversized_body, validate_audio
from app.config import ConfigError, Settings, load_settings
from app.main import create_app
from tests.helpers import make_settings

MAX = 1024


@pytest.mark.parametrize("name,ctype,expected", [
    ("a.webm", "audio/webm;codecs=opus", ("audio.webm", "audio/webm")),
    ("Voice.WAV", "application/octet-stream", ("audio.wav", "audio/wav")),
    ("blob", "audio/ogg", ("audio.ogg", "audio/ogg")),
    (None, "audio/mpeg", ("audio.mp3", "audio/mpeg")),
    ("ghi am cua toi.m4a", None, ("audio.m4a", "audio/mp4"))])
def test_accepted_formats_use_neutral_filename(name, ctype, expected):
    ok = validate_audio(name, ctype, b"x" * 10, MAX)
    assert (ok.filename, ok.content_type) == expected


@pytest.mark.parametrize("name,ctype", [("notes.txt", "text/plain"), (None, None), ("a.exe", "application/octet-stream")])
def test_wrong_type_is_415(name, ctype):
    with pytest.raises(ApiError) as err:
        validate_audio(name, ctype, b"x", MAX)
    assert (err.value.status_code, err.value.error) == (415, "invalid_audio")


def test_empty_file_is_415_and_oversize_is_413():
    with pytest.raises(ApiError) as err:
        validate_audio("a.wav", "audio/wav", b"", MAX)
    assert (err.value.status_code, err.value.error) == (415, "invalid_audio")
    with pytest.raises(ApiError) as err:
        validate_audio("a.wav", "audio/wav", b"x" * (MAX + 1), MAX)
    assert (err.value.status_code, err.value.error) == (413, "audio_too_long")
    assert validate_audio("a.wav", "audio/wav", b"x" * MAX, MAX).data  # dung bang gioi han thi qua


def test_parse_client_time_accepts_epoch_ms_and_iso_8601():
    assert parse_client_time("1764079204000") == 1764079204.0
    assert parse_client_time("2026-11-25T14:00:00Z") == parse_client_time("2026-11-25T14:00:00+00:00")
    assert parse_client_time("2026-11-25T14:00:00") == parse_client_time("2026-11-25T14:00:00Z")  # khong mui gio = UTC
    assert parse_client_time("2026-11-25T21:00:00+07:00") == parse_client_time("2026-11-25T14:00:00Z")
    assert parse_client_time("2026-11-25T14:00:00.123Z") - parse_client_time("2026-11-25T14:00:00Z") == pytest.approx(0.123)
    assert parse_client_time(None) is None and parse_client_time("  ") is None


@pytest.mark.parametrize("bad", ["hom qua", "nan", "inf", "2026-13-45"])
def test_parse_client_time_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_client_time(bad)


def test_oversized_content_length_is_rejected_before_parsing():
    reject_oversized_body("100", MAX)
    reject_oversized_body(None, MAX)
    reject_oversized_body("khong phai so", MAX)
    with pytest.raises(ApiError) as err:
        reject_oversized_body(str(MAX + 70 * 1024), MAX)
    assert err.value.error == "audio_too_long"


def test_upload_spool_threshold_covers_max_upload_so_audio_never_rolls_to_disk():
    settings = make_settings(max_upload_mb=10)
    create_app(settings)
    threshold = getattr(MultiPartParser, "spool_max_size", None) or getattr(MultiPartParser, "max_file_size")
    assert threshold >= settings.max_upload_bytes


def test_defaults_match_data_model_table():
    s = Settings()
    assert (s.blaze_base_url, s.stt_model, s.tts_model, s.tts_voices) == (
        "https://api.blaze.vn", "blaze-stt-1.5", "blaze-tts-1.5-realtime", ("HN-Nam-2-BL",))
    assert (s.max_upload_mb, s.max_audio_s, s.max_tts_chars, s.provider_retries, s.long_pause_s,
            s.fillers_supported, s.max_keywords, s.app_env) == (10, 300, 1000, 2, 2.0, True, 100, "dev")
    assert s.provider_timeout_s == 60 and s.parallel_provider_calls is False  # theo ket qua spike


def test_load_settings_reads_env_and_splits_voice_list():
    s = load_settings({"BLAZE_API_KEY": " k ", "VOICE_TTS_VOICES": "HN-Nam-2-BL, SG-Nu-1 ,", "VOICE_MAX_UPLOAD_MB": "2.5",
                       "VOICE_PARALLEL_PROVIDER_CALLS": "TRUE", "BLAZE_BASE_URL": "https://x.test/",
                       "VOICE_FILLERS": "ừm, kiểu như"})
    assert s.blaze_api_key == "k" and s.tts_voices == ("HN-Nam-2-BL", "SG-Nu-1") and s.default_voice == "HN-Nam-2-BL"
    assert s.max_upload_mb == 2.5 and s.parallel_provider_calls is True and s.blaze_base_url == "https://x.test"
    assert s.fillers == ("ừm", "kiểu như")


@pytest.mark.parametrize("env", [{"VOICE_MAX_UPLOAD_MB": "0"}, {"VOICE_MAX_AUDIO_S": "-3"}, {"VOICE_LONG_PAUSE_S": "abc"},
                                 {"VOICE_PROVIDER_RETRIES": "-1"}, {"VOICE_FILLERS_SUPPORTED": "maybe"},
                                 {"VOICE_MAX_TTS_CHARS": "1.5"}])
def test_invalid_config_values_raise(env):
    with pytest.raises(ConfigError):
        load_settings(env)


def test_zero_retries_is_allowed():
    assert load_settings({"VOICE_PROVIDER_RETRIES": "0"}).provider_retries == 0
