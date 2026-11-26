"""Bo do voice (spec 015 T027) chay tren voice-service gia (httpx.MockTransport): khong mang, khong key, khong credit."""
import json

import httpx
import pytest

from evals.build_manifest import ref_hash
from evals.eval_inputs import load_phrases
from evals.run_voice_eval import parse_args, run

GOLDEN_ROWS = [
    {"id": "g1", "qid": "q1", "track": "java_backend", "intended_tier": "strong", "question": "HashMap là gì?",
     "answer": "HashMap không thread-safe nên dùng ConcurrentHashMap"},
    {"id": "g2", "qid": "q2", "track": "java_backend", "intended_tier": "weak", "question": "Câu hỏi hai?",
     "answer": "em không rõ"},
]
FREE_SECRET = "noi dung rieng tu cua nguoi ghi"
TOKEN = "eval-token-not-real"
HEALTH = httpx.Response(200, json={"status": "ok", "provider": "blaze"})


class FakeVoiceService:
    def __init__(self, provider="blaze"):
        self.provider = provider
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok", "provider": self.provider})
        if request.url.path == "/api/voice/speak":
            return httpx.Response(200, content=b"\xff\xfb" * 100, headers={"content-type": "audio/mpeg"})
        body = request.read()
        if b"free" in body:  # file audio cua clip free
            text = FREE_SECRET
        elif b'name="keywords"' in body:
            text = "HashMap không thread-safe nên dùng ConcurrentHashMap"
        else:
            text = "hát mắp không thờ rét sếp nên dùng con ca rừn"
        return httpx.Response(200, json={
            "no_speech": False, "transcript": text, "segments": [{"start": 0.5, "end": 12.0}],
            "metrics": {"speech_time_s": 11.5, "speech_rate_spm": 140.0, "long_pause_count": 0, "filler_ratio": 0.02},
            "warnings": ["keywords_truncated"], "provider": {"stt_model": "blaze-stt-1.5", "stt_ms": 900}})


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("VOICE_SERVICE_INTERNAL_TOKEN", TOKEN)
    golden = tmp_path / "golden.jsonl"
    golden.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in GOLDEN_ROWS), encoding="utf-8")
    manifest = tmp_path / "manifest.jsonl"
    rows = [{"clip_id": "r01", "golden_id": "g1", "ref_sha256": ref_hash(GOLDEN_ROWS[0]["answer"]), "speaker": "s1",
             "kind": "read", "track": "java_backend"},
            {"clip_id": "r02", "golden_id": "g2", "ref_sha256": ref_hash(GOLDEN_ROWS[1]["answer"]), "speaker": "s2",
             "kind": "read", "track": "java_backend"},
            {"clip_id": "f01", "speaker": "s1", "kind": "free", "track": "java_backend"}]
    manifest.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    audio, phrases = tmp_path / "audio", tmp_path / "phrases"
    audio.mkdir()
    phrases.mkdir()
    (phrases / "java_backend.json").write_text(json.dumps({"phrases": ["HashMap", "ConcurrentHashMap", "thread-safe"]}),
                                               encoding="utf-8")
    argv = ["--out", str(tmp_path / "report.md"), "--manifest", str(manifest), "--golden", str(golden),
            "--audio-dir", str(audio), "--phrases-dir", str(phrases), "--out-dir", str(tmp_path / "out")]
    return tmp_path, audio, argv


def test_no_recordings_exits_2_without_report(setup):
    tmp_path, _, argv = setup
    fake = FakeVoiceService()
    assert run(parse_args(argv), transport=httpx.MockTransport(fake)) == 2
    assert not (tmp_path / "report.md").exists() and fake.requests == []


def test_service_not_ready_stops_before_measuring(setup):
    tmp_path, audio, argv = setup
    (audio / "r01.wav").write_bytes(b"RIFFread")
    fake = FakeVoiceService(provider="unconfigured")
    assert run(parse_args(argv), transport=httpx.MockTransport(fake)) == 1
    assert [r.url.path for r in fake.requests] == ["/api/health"]

    def down(request):
        raise httpx.ConnectError("refused", request=request)

    assert run(parse_args(argv), transport=httpx.MockTransport(down)) == 1
    assert not (tmp_path / "report.md").exists()


def test_full_run_writes_report_samples_and_raw_log(setup, capsys):
    tmp_path, audio, argv = setup
    (audio / "r01.webm").write_bytes(b"read-audio")
    (audio / "f01.wav").write_bytes(b"free-audio")
    fake = FakeVoiceService()
    assert run(parse_args(argv), transport=httpx.MockTransport(fake)) == 0

    transcribes = [r for r in fake.requests if r.url.path == "/api/voice/transcribe"]
    assert len(transcribes) == 3  # r01 co + khong keywords, f01 mot lan
    for r in transcribes:
        assert r.headers["x-internal-token"] == TOKEN and int(r.headers["content-length"]) > 0
        assert b'name="consent_confirmed"\r\n\r\ntrue' in r.content
    assert [b'name="keywords"' in r.content for r in transcribes] == [True, False, True]
    assert len([r for r in fake.requests if r.url.path == "/api/voice/speak"]) == 3  # khoi dong + 2 cau golden

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Clip có file: 2/3 (thiếu: r02); đã đo 2 clip" in report
    assert "| có keywords (mọi clip) | 1 |" in report and "4/4 | 100.0%" in report and "0/4 | 0.0%" in report
    assert "| ≤ 30 s | 2 |" in report and "Lượt có keywords lỗi (không có độ dài): 0." in report
    assert "| r01 | s1 | java_backend | strong |" in report and "| f01 | s1 | java_backend | 11.5 | 140 |" in report
    printed = capsys.readouterr()
    for text in (report, printed.out, printed.err):
        assert FREE_SECRET not in text and TOKEN not in text
    samples = (tmp_path / "out" / "stt_samples.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(s) for s in samples] == [{"id": "r01-stt", "stt_of": "g1", "noise": ["real_stt"],
                                                 "answer": "HashMap không thread-safe nên dùng ConcurrentHashMap"}]
    raw = [json.loads(line) for line in (tmp_path / "out" / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r.get("mode") for r in raw] == ["kw", "nokw", "kw", None, None]  # 3 STT + 2 TTS, khong co khoi dong


def test_fatal_code_stops_without_report(setup):
    tmp_path, audio, argv = setup
    (audio / "r01.wav").write_bytes(b"RIFFread")
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/health":
            return HEALTH
        return httpx.Response(402, json={"error": "quota_exceeded", "message": "het credit", "details": {}})

    assert run(parse_args(argv), transport=httpx.MockTransport(handler)) == 1
    assert calls == ["/api/health", "/api/voice/transcribe"] and not (tmp_path / "report.md").exists()
    assert (tmp_path / "out" / "raw.jsonl").read_text(encoding="utf-8").count("quota_exceeded") == 1


def test_provider_error_is_reported_not_retried_and_blocks_latency_verdict(setup):
    tmp_path, audio, argv = setup
    (audio / "r01.wav").write_bytes(b"RIFFread")
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/health":
            return HEALTH
        return httpx.Response(504, json={"error": "provider_timeout", "message": "cham", "details": {}})

    assert run(parse_args(argv + ["--skip-tts"]), transport=httpx.MockTransport(handler)) == 0
    assert calls.count("/api/voice/transcribe") == 2  # kw + nokw, khong thu lai
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "- r01 (kw): `provider_timeout`" in report and "- r01 (nokw): `provider_timeout`" in report
    assert "lỗi (không có độ dài): 1; có lượt lỗi nên không kết luận" in report
    assert "Không chạy (`--skip-tts`)" in report


def test_bad_200_body_becomes_error(setup):
    tmp_path, audio, argv = setup
    (audio / "r01.wav").write_bytes(b"RIFFread")

    def handler(request):
        return HEALTH if request.url.path == "/api/health" else httpx.Response(200, content=b"<html>proxy</html>")

    assert run(parse_args(argv + ["--skip-tts"]), transport=httpx.MockTransport(handler)) == 0
    assert "- r01 (kw): `bad_response`" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_load_phrases_fetches_and_caches(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"track": "x", "phrases": ["Redis", "Kafka"]})

    transport = httpx.MockTransport(handler)
    assert load_phrases("x", "http://ai", tmp_path, transport) == ["Redis", "Kafka"]
    assert load_phrases("x", "http://ai", tmp_path, transport) == ["Redis", "Kafka"]  # lan 2 doc cache
    assert seen == ["http://ai/api/stt/phrases?track=x"]
    assert json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))["generated_at"]
