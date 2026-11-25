"""BlazeClient.speak_stream: payload TTS, chunk dau, loi truoc byte dau (de route tra JSON)."""
import asyncio
import json

import httpx
import pytest

from app.api_error import ApiError
from app.blaze_client import BlazeClient
from tests.helpers import error_body, make_settings


class ChunkedBody(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


def speak(handler, **overrides):
    async def go():
        client = BlazeClient(make_settings(**overrides), transport=httpx.MockTransport(handler))
        stream = await client.speak_stream("Xin chào", "HN-Nam-2-BL")
        return b"".join([chunk async for chunk in stream])
    return asyncio.run(go())


def test_speech_payload_matches_spike_and_chunks_are_joined():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"], seen["path"] = json.loads(request.content), request.url.path
        return httpx.Response(200, headers={"content-type": "audio/mp3"}, stream=ChunkedBody([b"AAA", b"", b"BBB", b"C"]))

    assert speak(handler) == b"AAABBBC"
    assert seen["path"] == "/v1/audio/speech"
    assert seen["body"] == {"model": "blaze-tts-1.5-realtime", "input": "Xin chào", "voice": "HN-Nam-2-BL",
                            "response_format": "mp3"}  # speed / stream_format chi gui khi duoc cau hinh


def test_optional_speed_and_stream_format_are_sent_only_when_configured():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=b"AUDIO")

    speak(handler, tts_speed=1.2, tts_stream_format="audio")
    assert seen["body"]["speed"] == 1.2 and seen["body"]["stream_format"] == "audio"


def test_error_status_before_stream_raises_api_error():
    with pytest.raises(ApiError) as err:
        speak(lambda _r: httpx.Response(502, json=error_body("bad_gateway")), provider_retries=0)
    assert (err.value.status_code, err.value.error) == (502, "provider_error")


def test_retry_before_stream_then_ok():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, content=b"OK-AUDIO")

    assert speak(handler) == b"OK-AUDIO" and len(calls) == 2


def test_empty_audio_body_is_provider_error():
    with pytest.raises(ApiError) as err:
        speak(lambda _r: httpx.Response(200, content=b""))
    assert err.value.error == "provider_error"
