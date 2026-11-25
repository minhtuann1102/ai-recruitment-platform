"""BlazeClient (T012): multipart dung truong, Bearer, thu lai, doi ma loi. MockTransport, khong mang."""
import asyncio
import json

import httpx
import pytest

from app.api_error import ApiError
from app.blaze_client import BlazeClient
from tests.helpers import TEST_KEY, WAV, error_body, make_settings, stt_payload, vad_payload, words_for


def client_for(handler, **overrides) -> BlazeClient:
    return BlazeClient(make_settings(**overrides), transport=httpx.MockTransport(handler))


def run(coro):
    return asyncio.run(coro)


def stt_call(client: BlazeClient, **kw):
    return run(client.transcribe(WAV, "audio.webm", "audio/webm", **kw))


def test_transcribe_sends_expected_multipart_fields_and_bearer_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["ctype"] = request.headers["content-type"]
        seen["body"] = request.content
        seen["path"] = request.url.path
        return httpx.Response(200, json=stt_payload("xin chào HashMap", words_for("xin chào HashMap")))

    result = stt_call(client_for(handler), keywords=["HashMap", "ConcurrentHashMap"], language="vi")
    body = seen["body"]
    assert seen["path"] == "/v1/audio/transcriptions"
    assert seen["auth"] == f"Bearer {TEST_KEY}"
    assert seen["ctype"].startswith("multipart/form-data")
    assert b'name="file"; filename="audio.webm"' in body
    for field, value in (("model", "blaze-stt-1.5"), ("language", "vi"), ("timestamps", "true"), ("refine", "false"),
                         ("timeout", "60")):
        assert f'name="{field}"\r\n\r\n{value}\r\n'.encode() in body, field
    assert body.count(b'name="keywords"') == 2  # moi tu khoa mot truong form
    assert result.text == "xin chào HashMap" and result.model == "blaze-stt-1.5"
    assert len(result.word_timings) == 3


def test_transcribe_without_words_returns_empty_word_timings():
    """blaze-stt-1.0: segments chi co start / end / text, khong co words."""
    payload = {"id": "t", "status": "completed", "model": "blaze-stt-1.0", "text": "alo",
               "segments": [{"start": 0.1, "end": 0.9, "text": "alo", "raw_text": "alo", "speaker": None}]}
    result = stt_call(client_for(lambda _r: httpx.Response(200, json=payload)))
    assert result.word_timings == () and result.model == "blaze-stt-1.0"


def test_voice_activity_coerces_string_times_sorts_and_drops_bad_segments():
    payload = vad_payload((5, 6.5), (0.03096875, 2.5))
    payload["segments"] += [{"start": "3", "end": "3"}, {"start": "x", "end": "4"}, {"end": "4"}]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/voice_activity"
        assert b'name="file"' in request.content
        return httpx.Response(200, json=payload)

    segments = run(client_for(handler).voice_activity(WAV, "audio.wav", "audio/wav"))
    assert [(s.start, s.end) for s in segments] == [(0.03096875, 2.5), (5.0, 6.5)]


def test_retries_503_then_succeeds():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503, json=error_body("overloaded"))
        return httpx.Response(200, json=stt_payload("ok"))

    assert stt_call(client_for(handler)).text == "ok"
    assert len(calls) == 2


def test_429_exhausts_retries_then_rate_limited():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429, json=error_body("rate_limit_exceeded"))

    with pytest.raises(ApiError) as err:
        stt_call(client_for(handler, provider_retries=2))
    assert (err.value.status_code, err.value.error) == (429, "provider_rate_limited")
    assert len(calls) == 3  # lan dau + 2 lan thu lai


@pytest.mark.parametrize("status,body", [(402, error_body("payment_required")),
                                         (429, error_body("insufficient_quota", "insufficient_quota"))])
def test_out_of_credit_maps_to_quota_exceeded_without_retry(status, body):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(status, json=body)

    with pytest.raises(ApiError) as err:
        stt_call(client_for(handler))
    assert (err.value.status_code, err.value.error) == (402, "quota_exceeded")
    assert len(calls) == 1


@pytest.mark.parametrize("response", [httpx.Response(202, json={"status": "in_progress", "id": "t"}),
                                      httpx.Response(200, json={"status": "in_progress", "id": "t"})])
def test_stt_in_progress_maps_to_provider_timeout_without_retry(response):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return response

    with pytest.raises(ApiError) as err:
        stt_call(client_for(handler))
    assert (err.value.status_code, err.value.error) == (504, "provider_timeout")
    assert len(calls) == 1


@pytest.mark.parametrize("status,expected", [(400, (415, "invalid_audio")), (415, (415, "invalid_audio")),
                                             (413, (413, "audio_too_long")), (401, (502, "provider_error")),
                                             (500, (502, "provider_error"))])
def test_http_errors_map_to_contract_codes(status, expected):
    with pytest.raises(ApiError) as err:
        stt_call(client_for(lambda _r: httpx.Response(status, json=error_body("x")), provider_retries=0))
    assert (err.value.status_code, err.value.error) == expected


def test_provider_message_is_not_copied_into_error_details():
    handler = lambda _r: httpx.Response(400, json=error_body("bad_file", message="noi dung nhay cam cua ban ghi"))
    with pytest.raises(ApiError) as err:
        stt_call(client_for(handler))
    assert "nhay cam" not in json.dumps(err.value.details) + err.value.message
    assert err.value.details["provider_code"] == "bad_file"


def test_network_errors_retry_then_map():
    calls = []

    def connect_error(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("boom")

    with pytest.raises(ApiError) as err:
        stt_call(client_for(connect_error, provider_retries=2))
    assert (err.value.status_code, err.value.error) == (502, "provider_error") and len(calls) == 3

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    with pytest.raises(ApiError) as err:
        stt_call(client_for(timeout, provider_retries=0))
    assert (err.value.status_code, err.value.error) == (504, "provider_timeout")


def test_malformed_json_body_is_provider_error():
    with pytest.raises(ApiError) as err:
        stt_call(client_for(lambda _r: httpx.Response(200, content=b"<html>not json</html>")))
    assert err.value.error == "provider_error"
