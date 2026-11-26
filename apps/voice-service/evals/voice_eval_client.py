"""Client cua bo do: goi voice-service dang chay (khong goi thang Blaze, research R10) va do thoi gian phia ben goi.

- transcribe: audio gui dang bytes de httpx dat Content-Length (thieu -> 411), luon kem consent_confirmed=true.
- speak: stream, do thoi gian toi chunk dau (SC-003) va tong thoi gian.
Token noi bo doc tu VOICE_SERVICE_INTERNAL_TOKEN, chi dat vao header, khong in ra.
"""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import httpx

from .eval_inputs import AUDIO_TYPES


@dataclass
class TranscribeResult:
    ok: bool
    elapsed_s: float
    status: int
    error: Optional[str] = None  # ma loi cua contract (provider_error, quota_exceeded...)
    transcript: str = ""
    no_speech: bool = False
    speech_end_s: Optional[float] = None  # moc cuoi doan noi = do dai cau uoc luong
    metrics: Optional[Dict] = None
    warnings: List[str] = field(default_factory=list)
    stt_model: Optional[str] = None


@dataclass
class SpeakResult:
    ok: bool
    first_byte_s: Optional[float]
    total_s: float
    status: int
    error: Optional[str] = None
    audio_bytes: int = 0


def _error_code(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error") or response.status_code)
    except ValueError:
        return str(response.status_code)


class VoiceEvalClient:
    def __init__(self, base_url: str, token: str = "", timeout_s: float = 120,
                 transport: Optional[httpx.BaseTransport] = None):
        headers = {"X-Internal-Token": token} if token else {}
        self._client = httpx.Client(base_url=base_url, headers=headers, timeout=timeout_s, transport=transport)

    def close(self) -> None:
        self._client.close()

    def health(self) -> Dict:
        response = self._client.get("/api/health")
        response.raise_for_status()
        return response.json()

    def transcribe(self, audio: Path, keywords: Optional[Sequence[str]], language: str = "vi") -> TranscribeResult:
        data = {"consent_confirmed": "true", "language": language}
        if keywords:
            data["keywords"] = json.dumps(list(keywords), ensure_ascii=False)
        files = {"audio": (audio.name, audio.read_bytes(), AUDIO_TYPES.get(audio.suffix.lower(), "application/octet-stream"))}
        start = time.perf_counter()
        try:
            response = self._client.post("/api/voice/transcribe", data=data, files=files)
        except httpx.HTTPError as exc:  # mat ket noi / qua han phia client: ghi lai, khong thu lai (tranh tinh phi 2 lan)
            return TranscribeResult(ok=False, elapsed_s=time.perf_counter() - start, status=0, error=type(exc).__name__)
        elapsed = time.perf_counter() - start
        if response.status_code != 200:
            return TranscribeResult(ok=False, elapsed_s=elapsed, status=response.status_code, error=_error_code(response))
        body = response.json()
        segments = body.get("segments") or []
        return TranscribeResult(ok=True, elapsed_s=elapsed, status=200, transcript=body.get("transcript") or "",
                                no_speech=bool(body.get("no_speech")),
                                speech_end_s=max((s["end"] for s in segments), default=None),
                                metrics=body.get("metrics"), warnings=list(body.get("warnings") or []),
                                stt_model=(body.get("provider") or {}).get("stt_model"))

    def speak(self, text: str) -> SpeakResult:
        start = time.perf_counter()
        first_byte, size = None, 0
        try:
            with self._client.stream("POST", "/api/voice/speak", json={"text": text}) as response:
                if response.status_code != 200:
                    response.read()
                    return SpeakResult(ok=False, first_byte_s=None, total_s=time.perf_counter() - start,
                                       status=response.status_code, error=_error_code(response))
                for chunk in response.iter_bytes():
                    if chunk and first_byte is None:
                        first_byte = time.perf_counter() - start
                    size += len(chunk)
        except httpx.HTTPError as exc:  # stream dong giua chung = loi TTS (contract)
            return SpeakResult(ok=False, first_byte_s=first_byte, total_s=time.perf_counter() - start, status=0,
                               error=type(exc).__name__, audio_bytes=size)
        return SpeakResult(ok=size > 0, first_byte_s=first_byte, total_s=time.perf_counter() - start, status=200,
                           error=None if size else "empty_audio", audio_bytes=size)
