"""BlazeClient: chinh sach thu lai (H1: khong tinh phi hai lan), 202 khong phai JSON, doc moc theo tu nhieu hinh dang."""
import asyncio

import httpx
import pytest

from app.api_error import ApiError
from app.blaze_client import BlazeClient
from tests.helpers import WAV, error_body, make_settings, stt_payload


def stt(handler, **overrides):
    client = BlazeClient(make_settings(**overrides), transport=httpx.MockTransport(handler))
    return asyncio.run(client.transcribe(WAV, "audio.webm", "audio/webm"))


def vad(handler, **overrides):
    client = BlazeClient(make_settings(**overrides), transport=httpx.MockTransport(handler))
    return asyncio.run(client.voice_activity(WAV, "audio.webm", "audio/webm"))


def failing(exc, calls):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise exc
    return handler


@pytest.mark.parametrize("exc,expected", [(httpx.ConnectError("refused"), (502, "provider_error")),
                                          (httpx.ConnectTimeout("slow connect"), (504, "provider_timeout"))])
def test_connect_errors_are_retried_then_mapped(exc, expected):
    calls = []
    with pytest.raises(ApiError) as err:
        stt(failing(exc, calls), provider_retries=2)
    assert (err.value.status_code, err.value.error) == expected
    assert len(calls) == 3  # request chua toi Blaze: gui lai an toan


@pytest.mark.parametrize("exc,expected", [(httpx.ReadTimeout("slow"), (504, "provider_timeout")),
                                          (httpx.WriteTimeout("slow"), (504, "provider_timeout")),
                                          (httpx.ReadError("reset"), (502, "provider_error")),
                                          (httpx.RemoteProtocolError("bad"), (502, "provider_error"))])
def test_stt_is_never_retried_after_the_request_may_have_reached_blaze(exc, expected):
    calls = []
    with pytest.raises(ApiError) as err:
        stt(failing(exc, calls), provider_retries=2)
    assert (err.value.status_code, err.value.error) == expected
    assert len(calls) == 1  # gui lai = Blaze tinh phi STT lan nua


def test_vad_read_timeout_is_not_retried_either():
    calls = []
    with pytest.raises(ApiError) as err:
        vad(failing(httpx.ReadTimeout("slow"), calls), provider_retries=2)
    assert err.value.error == "provider_timeout" and len(calls) == 1


@pytest.mark.parametrize("status", [500, 502, 504])
def test_5xx_other_than_503_is_not_retried(status):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(status, json=error_body("boom"))

    with pytest.raises(ApiError) as err:
        stt(handler, provider_retries=2)
    assert (err.value.status_code, err.value.error) == (502, "provider_error") and len(calls) == 1


def test_503_is_retried_until_the_limit():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(ApiError) as err:
        stt(handler, provider_retries=2)
    assert err.value.error == "provider_error" and len(calls) == 3


@pytest.mark.parametrize("response", [httpx.Response(202), httpx.Response(202, content=b"<html>queued</html>"),
                                      httpx.Response(202, json={"id": "t", "status": "in_progress"})])
def test_202_without_json_body_is_still_provider_timeout(response):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return response

    with pytest.raises(ApiError) as err:
        stt(handler)
    assert (err.value.status_code, err.value.error) == (504, "provider_timeout") and len(calls) == 1


def test_word_timings_are_gathered_across_segments_coerced_sorted_and_clamped():
    payload = stt_payload("a b c d e")
    payload["segments"] = [
        {"id": 0, "startTime": 5, "endTime": 7, "text": "d e", "words": [
            {"text": "e", "start": "6.5", "end": "7.0"}, {"text": "d", "start": 5.0, "end": 5.4}]},  # chuoi + khong sap xep
        {"id": 1, "startTime": 0, "endTime": 3, "text": "a b c", "words": [
            {"text": "a", "start": 0.2, "end": 0.6}, {"text": "b", "start": 1.0, "end": 0.9},  # end < start
            {"text": "c", "start": "x", "end": 2.0}, {"text": "?", "end": 2.0}, "rac", {"text": "-1", "start": -1, "end": 0}]},
        {"id": 2, "text": "khong co words"}]
    result = stt(lambda _r: httpx.Response(200, json=payload))
    assert result.word_timings == ((0.2, 0.6), (1.0, 1.0), (5.0, 5.4), (6.5, 7.0))


def test_word_timings_are_empty_when_words_are_missing_or_not_lists():
    for segments in ([], [{"start": 0, "end": 1, "text": "x"}], [{"words": None}], [{"words": "khong phai danh sach"}], "sai"):
        payload = stt_payload("x")
        payload["segments"] = segments
        assert stt(lambda _r: httpx.Response(200, json=payload)).word_timings == ()


def test_vad_accepts_real_string_times_and_unsorted_segments():
    payload = {"segments": [{"transcription": "", "start": "9.5", "end": "10.0"},
                            {"transcription": "", "start": "0.03096875", "end": "9.68346875"}],
               "error_msg": "", "executing_time": 0.0}
    segments = vad(lambda _r: httpx.Response(200, json=payload))
    assert [(s.start, s.end) for s in segments] == [(0.03096875, 9.68346875), (9.5, 10.0)]
