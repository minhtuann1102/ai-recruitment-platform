"""BlazeClient.speak_stream: payload TTS, chunk dau, loi truoc byte dau (de route tra JSON)."""
import asyncio
import json

import httpx
import pytest

from app.api_error import ApiError
from app.blaze_client import BlazeClient
from tests.helpers import error_body, make_settings


class ChunkedBody(httpx.AsyncByteStream):
    """Body stream gia: phat tung chunk, tuy chon nem loi sau chunk cuoi; ghi nhan upstream da dong chua."""

    def __init__(self, chunks, then_raise=None):
        self.chunks, self.then_raise, self.closed = chunks, then_raise, False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.then_raise:
            raise self.then_raise

    async def aclose(self):
        self.closed = True


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
                            "response_format": "mp3"}  # dung 4 truong da xac nhan o spike


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


def test_error_in_the_middle_of_the_stream_propagates_and_closes_the_upstream_response():
    body = ChunkedBody([b"AAA", b"BBB"], then_raise=httpx.ReadError("cut"))

    async def go():
        client = BlazeClient(make_settings(), transport=httpx.MockTransport(lambda _r: httpx.Response(200, stream=body)))
        stream = await client.speak_stream("Xin chào", "HN-Nam-2-BL")
        got = []
        with pytest.raises(httpx.ReadError):
            async for chunk in stream:
                got.append(chunk)
        return got

    assert asyncio.run(go()) == [b"AAA", b"BBB"]
    assert body.closed is True  # khong ro ri ket noi toi Blaze


def test_stream_closed_by_consumer_early_closes_the_upstream_response():
    body = ChunkedBody([b"AAA", b"BBB", b"CCC"])

    async def go():
        client = BlazeClient(make_settings(), transport=httpx.MockTransport(lambda _r: httpx.Response(200, stream=body)))
        stream = await client.speak_stream("Xin chào", "HN-Nam-2-BL")
        await stream.aclose()  # route goi qua BackgroundTask khi client ngat

    asyncio.run(go())
    assert body.closed is True
