"""Client httpx cho Blaze (VAD, STT, TTS). Chi tiet endpoint: specs/015-voice-mode/research.md R3, R7, R8.

- Header `Authorization: Bearer <BLAZE_API_KEY>`; key chi doc tu Settings (env phia server).
- Thu lai (VOICE_PROVIDER_RETRIES, backoff co so VOICE_PROVIDER_BACKOFF_S * 2^n) cho loi mang, 5xx, 429 khong phai het
  credit. Het retry -> ApiError theo blaze_errors.py. 4xx khac khong thu lai. STT tra 202 / in_progress -> provider_timeout.
- Khong log noi dung (audio, ban ghi, keywords, van ban TTS), chi ma trang thai va ten loi.
- `transport` cho phep test thay bang httpx.MockTransport (khong mang, khong key).
"""
import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import httpx

from .api_error import ApiError
from .blaze_errors import is_retryable, map_status_error
from .blaze_speech_stream import SpeechStream
from .config import Settings
from .models import SpeechSegment

log = logging.getLogger("voice_service.blaze")
HTTP_MARGIN_S = 5.0  # httpx doi them de Blaze tu tra 202 (qua `timeout` cua STT) truoc khi ta ngat ket noi


@dataclass(frozen=True)
class SttResult:
    text: str
    model: str
    # moc (start, end) giay cua tung tu, sap theo start; rong neu model khong tra `words` (vd blaze-stt-1.0)
    word_timings: Tuple[Tuple[float, float], ...] = ()


def _finite_pair(start, end) -> Optional[Tuple[float, float]]:
    """(start, end) dang so (Blaze co luc tra chuoi "0.03"), hoac None neu hong. end < start thi nang end len = start."""
    try:
        start, end = float(start), float(end)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(start) and math.isfinite(end)) or start < 0:
        return None
    return start, max(start, end)


def _word_timings(payload: dict) -> Tuple[Tuple[float, float], ...]:
    """Gop `words` cua moi segment (spike 2026-11-25: segments[].words[] = {text, start, end}; blaze-stt-1.0 khong co
    words). Chi giu moc thoi gian: noi dung tu khong can nua (chi so tinh tu ban ghi `text`)."""
    containers = [s for s in payload.get("segments") or [] if isinstance(s, dict)] + [payload]
    pairs = []
    for box in containers:
        for word in box.get("words") or []:
            if isinstance(word, dict) and (pair := _finite_pair(word.get("start"), word.get("end"))):
                pairs.append(pair)
    return tuple(sorted(pairs))


def _json_object(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        raise ApiError(502, "provider_error", "Nhà cung cấp giọng nói trả dữ liệu không đúng định dạng")
    return payload


class BlazeClient:
    def __init__(self, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None):
        self._s = settings
        # ket noi dau tien co luc loi ConnectError tren mot so may (spike): transport tu thu lai 3 lan truoc retry cua ta
        self._client = httpx.AsyncClient(
            base_url=settings.blaze_base_url, transport=transport or httpx.AsyncHTTPTransport(retries=3),
            headers={"Authorization": f"Bearer {settings.blaze_api_key}"},
            timeout=httpx.Timeout(settings.provider_timeout_s + HTTP_MARGIN_S))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _send(self, call: str, make_request: Callable[[], httpx.Request], audio: bool,
                    stream: bool = False) -> httpx.Response:
        """Gui request (build lai moi lan thu), tra response 2xx hoac nem ApiError sau khi het lan thu lai."""
        attempts = self._s.provider_retries + 1
        for attempt in range(attempts):
            try:
                response = await self._client.send(make_request(), stream=stream)
            except httpx.TimeoutException:
                error = ApiError(504, "provider_timeout", "Nhà cung cấp giọng nói phản hồi quá thời gian")
            except httpx.TransportError:
                error = ApiError(502, "provider_error", "Không kết nối được tới nhà cung cấp giọng nói")
            else:
                if response.status_code < 400:
                    return response
                body = await response.aread()
                await response.aclose()
                status = response.status_code
                error = map_status_error(status, body, audio)
                if status in (401, 403):
                    log.warning("provider_key_rejected call=%s status=%s", call, status)
                if not is_retryable(status, body):
                    raise error
            if attempt == attempts - 1:
                raise error
            log.info("provider_retry call=%s attempt=%d error=%s", call, attempt + 1, error.error)
            await asyncio.sleep(self._s.provider_backoff_s * 2 ** attempt)
        raise AssertionError("unreachable")  # vong lap luon return hoac raise

    def _upload_request(self, path: str, audio: bytes, filename: str, content_type: str,
                        data: Optional[dict] = None) -> Callable[[], httpx.Request]:
        return lambda: self._client.build_request(
            "POST", path, files={"file": (filename, audio, content_type)}, data=data)

    async def voice_activity(self, audio: bytes, filename: str, content_type: str) -> List[SpeechSegment]:
        """POST /v1/audio/voice_activity -> cac doan co tieng, sap theo start (start / end co the la chuoi: ep sang so).
        Bo doan hong (end <= start). Spike: VAD tho (gop cau tra loi 9.6 s co nhieu quang ngung thanh mot doan), nen chi
        dung de chan "khong co tieng" truoc khi goi STT; moc chi tiet lay tu `words` cua STT."""
        response = await self._send("vad", self._upload_request("/v1/audio/voice_activity", audio, filename, content_type),
                                    audio=True)
        segments = []
        for item in _json_object(response).get("segments") or []:
            try:
                segments.append(SpeechSegment(start=float(item["start"]), end=float(item["end"])))
            except (KeyError, TypeError, ValueError):  # ValidationError la con cua ValueError
                continue
        return sorted(segments, key=lambda s: s.start)

    async def transcribe(self, audio: bytes, filename: str, content_type: str, keywords: Sequence[str] = (),
                         language: str = "vi") -> SttResult:
        """POST /v1/audio/transcriptions. 202 / status in_progress (qua `timeout`) -> provider_timeout, khong thu lai."""
        data = {"model": self._s.stt_model, "language": language, "timestamps": "true",
                "refine": "true" if self._s.stt_refine else "false", "timeout": str(max(1, int(self._s.provider_timeout_s)))}
        if keywords:
            data["keywords"] = list(keywords)  # httpx lap truong form cho moi phan tu
        response = await self._send("stt", self._upload_request("/v1/audio/transcriptions", audio, filename, content_type,
                                                                data), audio=True)
        payload = _json_object(response)
        if response.status_code == 202 or payload.get("status") == "in_progress":
            raise ApiError(504, "provider_timeout", "Nhận dạng giọng nói chưa xong trong thời gian cho phép")
        text = payload.get("text")
        if not isinstance(text, str):
            raise ApiError(502, "provider_error", "Nhà cung cấp giọng nói không trả bản ghi")
        return SttResult(text=text.strip(), model=str(payload.get("model") or self._s.stt_model),
                         word_timings=_word_timings(payload))

    async def speak_stream(self, text: str, voice: str) -> SpeechStream:
        """POST /v1/audio/speech -> SpeechStream mp3. Da kiem status va doc chunk dau: loi thi nem ApiError (route tra JSON)."""
        payload = {"model": self._s.tts_model, "input": text, "voice": voice, "response_format": "mp3"}
        if self._s.tts_speed != 1.0:
            payload["speed"] = self._s.tts_speed
        if self._s.tts_stream_format:
            payload["stream_format"] = self._s.tts_stream_format
        response = await self._send(
            "tts", lambda: self._client.build_request("POST", "/v1/audio/speech", json=payload), audio=False, stream=True)
        return await SpeechStream.open(response)
