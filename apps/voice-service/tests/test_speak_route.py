"""POST /api/voice/speak (T022): stream audio/mpeg, kiem dau vao truoc khi goi Blaze, loi truoc byte dau tra JSON."""
import json

import httpx
import pytest

from tests.helpers import FakeBlaze, error_body
from tests.test_blaze_client_speech import ChunkedBody

SPEECH = "/v1/audio/speech"


def speech_blaze(*chunks) -> FakeBlaze:
    # Blaze that tra content-type audio/mp3; endpoint cua ta van phai tra audio/mpeg
    return FakeBlaze({SPEECH: lambda _r: httpx.Response(200, headers={"content-type": "audio/mp3"},
                                                        stream=ChunkedBody(list(chunks)))})


def test_three_chunks_are_streamed_back_as_audio_mpeg(build_client):
    fake = speech_blaze(b"ID3-first", b"-second", b"-third")
    r = build_client(fake).post("/api/voice/speak", json={"text": "HashMap và ConcurrentHashMap khác nhau thế nào?"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.headers["cache-control"] == "no-store"
    assert r.content == b"ID3-first-second-third"
    assert len(fake.requests) == 1
    assert fake.requests[0].headers["authorization"].startswith("Bearer ")


def test_default_voice_and_allowed_voice_selection(build_client):
    fake = speech_blaze(b"A")
    client = build_client(fake, tts_voices=("HN-Nam-2-BL", "SG-Nu-1"))
    client.post("/api/voice/speak", json={"text": "Một"})
    client.post("/api/voice/speak", json={"text": "Hai", "voice": "SG-Nu-1"})
    sent = [json.loads(req.content) for req in fake.requests]
    assert [s["voice"] for s in sent] == ["HN-Nam-2-BL", "SG-Nu-1"]
    assert sent[0]["input"] == "Một" and sent[0]["response_format"] == "mp3"


@pytest.mark.parametrize("body,status,code", [
    ({"text": ""}, 400, "invalid_request"),
    ({"text": "   \n "}, 400, "invalid_request"),
    ({}, 400, "invalid_request"),
    ({"text": "x" * 1001}, 400, "text_too_long"),
    ({"text": "Xin chào", "voice": "Giong-La"}, 400, "invalid_voice")])
def test_invalid_input_never_reaches_blaze(build_client, body, status, code):
    fake = speech_blaze(b"A")
    r = build_client(fake).post("/api/voice/speak", json=body)
    assert (r.status_code, r.json()["error"]) == (status, code)
    assert set(r.json()) == {"error", "message", "details"}
    assert fake.requests == []


def test_text_at_exact_limit_is_accepted(build_client):
    assert build_client(speech_blaze(b"A")).post("/api/voice/speak", json={"text": "x" * 1000}).status_code == 200


def test_blaze_502_before_stream_returns_json_provider_error(build_client):
    fake = FakeBlaze({SPEECH: lambda _r: httpx.Response(502, json=error_body("bad_gateway"))})
    r = build_client(fake, provider_retries=0).post("/api/voice/speak", json={"text": "Xin chào"})
    assert r.status_code == 502 and r.headers["content-type"].startswith("application/json")
    assert r.json()["error"] == "provider_error"


@pytest.mark.parametrize("status,body,expected", [(402, error_body("payment_required"), (402, "quota_exceeded")),
                                                  (429, error_body("rate_limit"), (429, "provider_rate_limited"))])
def test_quota_and_rate_limit_errors_before_stream(build_client, status, body, expected):
    fake = FakeBlaze({SPEECH: lambda _r: httpx.Response(status, json=body)})
    r = build_client(fake, provider_retries=0).post("/api/voice/speak", json={"text": "Xin chào"})
    assert (r.status_code, r.json()["error"]) == expected


def test_provider_timeout_before_stream_is_504(build_client):
    def slow(_request):
        raise httpx.ReadTimeout("slow")
    r = build_client(FakeBlaze({SPEECH: slow}), provider_retries=0).post("/api/voice/speak", json={"text": "Xin chào"})
    assert (r.status_code, r.json()["error"]) == (504, "provider_timeout")
