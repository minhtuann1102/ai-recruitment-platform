"""POST /api/voice/transcribe: dong y, kiem dau vao truoc khi goi nha cung cap, rieng tu (khong log, khong ghi dia)."""
import logging
import tempfile

import httpx

import pytest

from tests.helpers import WAV, FakeBlaze, json_reply, stt_payload, vad_payload
from tests.test_transcribe_route import STT, VAD, post

SECRET_TRANSCRIPT = "mat khau noi bo la Zebra-Quasar-7"
SECRET_KEYWORD = "TuKhoaBiMatXyz"
SECRET_TEXT = "Cau hoi rieng tu ve Narwhal-Kestrel"


def quiet_blaze() -> FakeBlaze:
    return FakeBlaze({VAD: json_reply(vad_payload((0.0, 3.0))),
                      STT: json_reply(stt_payload(SECRET_TRANSCRIPT, [("mat", 0.1, 0.4), ("khau", 0.5, 0.9)]))})


@pytest.mark.parametrize("data", [{}, {"consent_confirmed": "false"}, {"consent_confirmed": "yes"}, {"consent_confirmed": "1"},
                                  {"consent_confirmed": ""}])
def test_missing_or_non_true_consent_is_400_and_blaze_gets_zero_requests(build_client, data):
    fake = quiet_blaze()
    client = build_client(fake)
    r = client.post("/api/voice/transcribe", files={"audio": ("a.webm", WAV, "audio/webm")}, data=data)
    assert (r.status_code, r.json()["error"]) == (400, "consent_required")
    assert fake.requests == []


def test_consent_true_is_case_insensitive(build_client):
    assert post(build_client(quiet_blaze()), consent_confirmed="True").status_code == 200


def test_consent_is_checked_before_audio_problems(build_client):
    fake = quiet_blaze()
    r = build_client(fake).post("/api/voice/transcribe", files={"audio": ("a.txt", b"", "text/plain")})
    assert r.json()["error"] == "consent_required" and fake.requests == []


@pytest.mark.parametrize("kwargs,status,code", [
    ({"name": "notes.txt", "ctype": "text/plain"}, 415, "invalid_audio"),
    ({"audio": b""}, 415, "invalid_audio"),
    ({"audio": b"x" * 5000}, 413, "audio_too_long")])
def test_bad_audio_is_rejected_without_calling_blaze(build_client, kwargs, status, code):
    fake = quiet_blaze()
    r = post(build_client(fake, max_upload_mb=0.002), **kwargs)  # ~2 KB
    assert (r.status_code, r.json()["error"]) == (status, code)
    assert fake.requests == []


def test_huge_body_is_rejected_by_content_length_before_parsing(build_client):
    fake = quiet_blaze()
    r = post(build_client(fake, max_upload_mb=0.001), audio=b"x" * (200 * 1024))
    assert (r.status_code, r.json()["error"]) == (413, "audio_too_long") and fake.requests == []


@pytest.mark.parametrize("data", [{"language": "fr"}, {"answer_limit_s": "0"}, {"answer_limit_s": "-5"},
                                  {"answer_limit_s": "abc"}, {"topic_id": "x" * 201}])
def test_bad_optional_fields_are_400_invalid_request(build_client, data):
    fake = quiet_blaze()
    r = post(build_client(fake), **data)
    assert (r.status_code, r.json()["error"]) == (400, "invalid_request") and fake.requests == []


def test_missing_audio_part_is_400_invalid_request(build_client):
    fake = quiet_blaze()
    r = build_client(fake).post("/api/voice/transcribe", data={"consent_confirmed": "true"})
    assert (r.status_code, r.json()["error"]) == (400, "invalid_request") and fake.requests == []


def test_logs_never_contain_transcript_keywords_or_filenames(build_client, caplog):
    caplog.set_level(logging.DEBUG)
    for name in ("httpx", "httpcore"):
        caplog.set_level(logging.DEBUG, logger=name)
    client = build_client(quiet_blaze())
    r = post(client, name="CV-cua-Nguyen-Van-A.webm", keywords=[SECRET_KEYWORD, "Khac"], topic_id="t")
    assert r.status_code == 200 and SECRET_TRANSCRIPT in r.text
    assert any(rec.name == "voice_service" for rec in caplog.records)  # test khong rong: service co ghi log
    for secret in (SECRET_TRANSCRIPT, SECRET_KEYWORD, "Zebra", "Nguyen-Van-A"):
        assert secret not in caplog.text


def test_speak_text_is_never_logged(build_client, caplog):
    caplog.set_level(logging.DEBUG)
    fake = FakeBlaze({"/v1/audio/speech": lambda _r: httpx.Response(200, content=b"MP3")})
    r = build_client(fake).post("/api/voice/speak", json={"text": SECRET_TEXT})
    assert r.status_code == 200
    assert "Narwhal" not in caplog.text and SECRET_TEXT not in caplog.text


def test_audio_larger_than_default_spool_size_never_rolls_over_to_disk(build_client, monkeypatch):
    def forbidden(self):
        raise AssertionError("audio bi cuon ra dia")
    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", forbidden)
    r = post(build_client(quiet_blaze()), audio=b"\x00" * (3 * 1024 * 1024))  # 3 MB > nguong mac dinh 1 MB cua Starlette
    assert r.status_code == 200
