"""POST /api/voice/transcribe (T020): luong day du, no_speech, VAD du phong, canh bao. Blaze gia, khong mang."""
import httpx
import pytest

from tests.helpers import WAV, FakeBlaze, error_body, json_reply, stt_payload, vad_payload

VAD, STT = "/v1/audio/voice_activity", "/v1/audio/transcriptions"
TEXT = "Ừm, HashMap không thread-safe. Còn ConcurrentHashMap"
WORDS = [("Ừm,", 1.2, 1.6), ("HashMap", 1.7, 2.3), ("không", 2.4, 2.8), ("thread-safe.", 2.9, 3.6),  # roi nghi 3.2 s
         ("Còn", 6.8, 7.1), ("ConcurrentHashMap", 7.2, 8.4)]


def post(client, audio=WAV, name="answer.webm", ctype="audio/webm", **data):
    return client.post("/api/voice/transcribe", files={"audio": (name, audio, ctype)},
                       data={"consent_confirmed": "true", **data})


def happy_blaze(**routes) -> FakeBlaze:
    return FakeBlaze({VAD: json_reply(vad_payload((0.03096875, 9.68346875))),
                      STT: json_reply(stt_payload(TEXT, WORDS)), **routes})


def test_full_flow_returns_transcript_word_based_spans_and_metrics(build_client):
    fake = happy_blaze()
    r = post(build_client(fake), keywords=["HashMap", "ConcurrentHashMap"], topic_id="java.collections",
             question_audio_ended_at="1764079200000", recording_started_at="2025-11-25T14:00:04.000Z", answer_limit_s="7")
    assert r.status_code == 200
    body = r.json()
    assert fake.paths() == [VAD, STT]  # tuan tu: VAD truoc, STT sau
    assert body["no_speech"] is False and body["transcript"] == TEXT
    assert body["segments"] == [{"start": 1.2, "end": 3.6}, {"start": 6.8, "end": 8.4}]  # cat o quang ngung dai
    m = body["metrics"]
    assert m == {"topic_id": "java.collections", "thinking_time_s": 5.2, "answer_duration_s": 7.2, "over_limit": True,
                 "speech_time_s": 4.0, "speech_rate_spm": 105.0, "long_pause_count": 1, "filler_ratio": 0.143}
    assert body["warnings"] == []
    assert body["provider"]["stt_model"] == "blaze-stt-1.5" and body["provider"]["stt_ms"] >= 0
    assert fake.requests[1].content.count(b'name="keywords"') == 2


def test_response_never_contains_stt_confidence_even_if_provider_sends_one(build_client):
    payload = stt_payload(TEXT, WORDS)
    payload["confidence"] = 0.91
    payload["segments"][0]["confidence"] = 0.88
    r = post(build_client(happy_blaze(**{STT: json_reply(payload)})))
    assert "confidence" not in r.text and "0.91" not in r.text


def test_silence_returns_no_speech_without_calling_stt(build_client):
    fake = happy_blaze(**{VAD: json_reply(vad_payload())})
    r = post(build_client(fake))
    assert r.status_code == 200
    body = r.json()
    assert body["no_speech"] is True and body["transcript"] == "" and body["segments"] == [] and body["metrics"] is None
    assert body["provider"]["stt_ms"] is None
    assert fake.paths() == [VAD]


def test_stt_without_words_falls_back_to_vad_segments(build_client):
    """blaze-stt-1.0: khong co words -> cung cong thuc tren doan VAD; quang ngung 3 s giua hai doan."""
    payload = {"id": "t", "status": "completed", "model": "blaze-stt-1.0", "text": "một hai ba bốn năm sáu",
               "segments": [{"start": 0.0, "end": 9.0, "text": "x", "raw_text": "x", "speaker": None}]}
    fake = happy_blaze(**{VAD: json_reply(vad_payload((1.0, 4.0), (7.0, 9.0))), STT: json_reply(payload)})
    body = post(build_client(fake)).json()
    assert body["segments"] == [{"start": 1.0, "end": 4.0}, {"start": 7.0, "end": 9.0}]
    assert body["metrics"]["answer_duration_s"] == 8.0 and body["metrics"]["long_pause_count"] == 1
    assert body["metrics"]["speech_time_s"] == 5.0 and body["metrics"]["speech_rate_spm"] == 72.0
    assert body["provider"]["stt_model"] == "blaze-stt-1.0"


def test_keywords_longer_than_64_chars_are_dropped_with_a_warning(build_client):
    fake = happy_blaze()
    body = post(build_client(fake), keywords=["HashMap", "x" * 65, "y" * 64]).json()
    assert fake.requests[1].content.count(b'name="keywords"') == 2  # HashMap + chuoi 64 ky tu
    assert b"x" * 65 not in fake.requests[1].content and body["warnings"] == ["keywords_truncated"]


def test_keywords_json_array_dedupe_and_truncation_warning(build_client):
    fake = happy_blaze()
    body = post(build_client(fake, max_keywords=2), keywords='["HashMap", "Spring", "HashMap", "Kafka"]').json()
    assert fake.requests[1].content.count(b'name="keywords"') == 2
    assert body["warnings"] == ["keywords_truncated"]


@pytest.mark.parametrize("extra,warns", [({"recording_started_at": "1764079204000"}, True),
                                         ({"question_audio_ended_at": "hom qua", "recording_started_at": "1"}, True),
                                         # epoch GIAY (Date.now() / 1000): doc nham thanh ms se lech 1000 lan, phai bi tu choi
                                         ({"question_audio_ended_at": "1764079200", "recording_started_at": "1764079205"}, True),
                                         ({}, False)])
def test_bad_or_partial_client_timestamps_warn_but_do_not_fail(build_client, extra, warns):
    body = post(build_client(happy_blaze()), **extra).json()
    assert body["metrics"]["thinking_time_s"] is None
    assert ("invalid_client_timestamps" in body["warnings"]) is warns


def test_empty_transcript_with_speech_adds_warning(build_client):
    fake = happy_blaze(**{STT: json_reply(stt_payload("", []))})
    body = post(build_client(fake)).json()
    assert body["transcript"] == "" and "empty_transcript" in body["warnings"] and body["metrics"]["speech_rate_spm"] is None


def test_provider_errors_use_contract_codes(build_client):
    cases = [(STT, httpx.Response(402, json=error_body("payment_required")), 402, "quota_exceeded"),
             (STT, httpx.Response(202, json={"status": "in_progress"}), 504, "provider_timeout"),
             (VAD, httpx.Response(429, json=error_body("rate_limit")), 429, "provider_rate_limited"),
             (VAD, httpx.Response(503), 502, "provider_error"),
             (VAD, httpx.Response(400, json=error_body("bad_audio")), 415, "invalid_audio")]
    for path, response, status, code in cases:
        fake = happy_blaze(**{path: lambda _r, resp=response: resp})
        r = post(build_client(fake, provider_retries=0))
        assert (r.status_code, r.json()["error"]) == (status, code)
        assert set(r.json()) == {"error", "message", "details"}


@pytest.mark.parametrize("spans", [((0.0, 400.0),), ((0.0, 400.0), (10.0, 20.0))])  # doan cuoi theo start co the ngan hon
def test_vad_speech_end_beyond_max_audio_is_413_before_stt(build_client, spans):
    fake = happy_blaze(**{VAD: json_reply(vad_payload(*spans))})
    r = post(build_client(fake, max_audio_s=300))
    assert (r.status_code, r.json()["error"]) == (413, "audio_too_long")
    assert fake.paths() == [VAD]


def test_stt_read_timeout_is_one_request_and_504_not_a_billed_retry(build_client):
    def slow(_request):
        raise httpx.ReadTimeout("slow")
    fake = happy_blaze(**{STT: slow})
    r = post(build_client(fake, provider_retries=2))
    assert (r.status_code, r.json()["error"]) == (504, "provider_timeout")
    assert fake.paths() == [VAD, STT]  # dung mot lan STT
