"""Ham dung chung cho test: Settings tuong minh, Blaze gia (httpx.MockTransport), mau response that cua Blaze.

Hinh dang response theo spike 2026-11-25 (research.md "Ket qua spike"): VAD tra start / end dang CHUOI, STT tra
segments[].words[] va khong co do tin cay.
"""
import json
from dataclasses import replace
from typing import Callable, List

import httpx

from app.config import Settings

TEST_KEY = "test-key-not-real"
TEST_TOKEN = "test-internal-token"
WAV = b"RIFF$\x00\x00\x00WAVEfmt " + b"\x00" * 64  # noi dung khong quan trong: nha cung cap la gia


def make_settings(**overrides) -> Settings:
    """Settings cho test: co key gia, khong cho ngu khi thu lai (provider_backoff_s=0)."""
    return replace(Settings(blaze_api_key=TEST_KEY, provider_backoff_s=0), **overrides)


class FakeBlaze:
    """MockTransport ghi lai moi request toi Blaze. `routes`: path -> ham(request) -> httpx.Response."""

    def __init__(self, routes: dict):
        self.routes = routes
        self.requests: List[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.routes[request.url.path](request)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    def paths(self) -> List[str]:
        return [r.url.path for r in self.requests]


def json_reply(payload: dict, status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _req: httpx.Response(status, json=payload)


def error_body(code: str = "", kind: str = "", message: str = "") -> dict:
    return {"error": {"message": message, "type": kind, "code": code, "param": None}}


def vad_payload(*spans) -> dict:
    """VAD that: start / end la CHUOI, co truong thua."""
    return {"segments": [{"transcription": "", "start": str(s), "end": str(e)} for s, e in spans],
            "error_msg": "", "executing_time": 0.0}


def stt_payload(text: str, words=(), model: str = "blaze-stt-1.5") -> dict:
    """STT that: segments[] {id, startTime, endTime, text, speaker, words[{text,start,end}]}. Khong co do tin cay."""
    return {"id": "tr_1", "object": "transcription", "status": "completed", "model": model, "created_at": 1764079200,
            "filename": "audio.webm", "text": text, "raw_text": text,
            "segments": [{"id": 0, "startTime": words[0][1] if words else 0.0, "endTime": words[-1][2] if words else 0.0,
                          "text": text, "speaker": None,
                          "words": [{"text": t, "start": s, "end": e} for t, s, e in words]}]}


def words_for(text: str, start: float = 0.0, step: float = 0.3):
    """Moc tu deu nhau cho moi token cua `text`: (text, start, end)."""
    return [(w, round(start + i * step, 3), round(start + i * step + step * 0.8, 3)) for i, w in enumerate(text.split())]


def error_of(response) -> str:
    return json.loads(response.text)["error"]
