"""POST /api/voice/transcribe: audio -> VAD (cong "co tieng") -> STT -> ban ghi goc + doan co tieng + chi so luot.

Thu tu kiem (contract): Content-Length -> dong y (400 consent_required, TRUOC moi lan goi nha cung cap) -> truong tuy chon
-> tep audio -> cau hinh nha cung cap (503). Mac dinh tuan tu: VAD truoc, khong co tieng thi tra no_speech va KHONG goi STT
(tiet kiem credit; goi Starter 1 luong). VOICE_PARALLEL_PROVIDER_CALLS=true: goi VAD + STT cung luc (nhanh hon, nhung
STT van chay du VAD rong va gioi han VOICE_MAX_AUDIO_S chi chan duoc sau khi STT xong).
Rieng tu: khong ghi audio ra dia, khong log ban ghi / keywords, response khong co stt_confidence.
"""
import asyncio
import logging
import time
from typing import List, Optional, Tuple

from fastapi import APIRouter, Request

from . import metrics
from .api_error import ApiError
from .app_state import get_settings, require_blaze
from .audio_validation import ValidatedAudio, reject_oversized_body, validate_audio
from .blaze_client import BlazeClient, SttResult
from .config import Settings
from .delivery_metrics import WARN_INVALID_TIMESTAMPS, compute_turn_metrics, speech_spans
from .models import ProviderInfo, SpeechSegment, TranscriptionResult
from .transcribe_form import OPENAPI_REQUEST_BODY, TranscribeForm, parse_transcribe_form

log = logging.getLogger("voice_service")
router = APIRouter()


def _check_audio_length(segments: List[SpeechSegment], settings: Settings) -> None:
    if segments and segments[-1].end > settings.max_audio_s:
        raise ApiError(413, "audio_too_long", "Đoạn ghi âm dài hơn giới hạn cho phép",
                       {"max_audio_s": settings.max_audio_s})


async def _call_providers(blaze: BlazeClient, settings: Settings, audio: ValidatedAudio, form: TranscribeForm
                          ) -> Tuple[List[SpeechSegment], int, Optional[SttResult], Optional[int]]:
    """(doan VAD, vad_ms, ket qua STT hoac None, stt_ms hoac None). STT None = khong co tieng, khong goi STT."""
    def vad():
        return metrics.timed("vad", blaze.voice_activity(audio.data, audio.filename, audio.content_type))

    def stt():
        return metrics.timed("stt", blaze.transcribe(audio.data, audio.filename, audio.content_type, form.keywords,
                                                     form.language))
    if settings.parallel_provider_calls:
        results = await asyncio.gather(vad(), stt(), return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result
        (segments, vad_ms), (stt_result, stt_ms) = results
        if not segments:
            return segments, vad_ms, None, None
        _check_audio_length(segments, settings)
        return segments, vad_ms, stt_result, stt_ms
    segments, vad_ms = await vad()
    if not segments:
        return segments, vad_ms, None, None
    _check_audio_length(segments, settings)
    stt_result, stt_ms = await stt()
    return segments, vad_ms, stt_result, stt_ms


@router.post("/api/voice/transcribe", response_model=TranscriptionResult, openapi_extra=OPENAPI_REQUEST_BODY)
async def transcribe(request: Request) -> TranscriptionResult:
    settings = get_settings(request)
    reject_oversized_body(request.headers.get("content-length"), settings.max_upload_bytes)
    async with request.form() as raw_form:
        form = parse_transcribe_form(raw_form, settings)
        audio = validate_audio(form.upload.filename, form.upload.content_type, await form.upload.read(),
                               settings.max_upload_bytes)
    blaze = require_blaze(request)

    warnings: List[str] = []
    if form.keywords_truncated:
        warnings.append("keywords_truncated")
    if form.timestamps_invalid:
        warnings.append(WARN_INVALID_TIMESTAMPS)

    started = time.perf_counter()
    vad_segments, vad_ms, stt, stt_ms = await _call_providers(blaze, settings, audio, form)
    if stt is None:  # VAD khong thay tieng: khong co ban ghi, khong chi so (FR-004)
        log.info("transcribe_done bytes=%d no_speech=true vad_ms=%d total_ms=%d", len(audio.data), vad_ms,
                 (time.perf_counter() - started) * 1000)
        return TranscriptionResult(no_speech=True, transcript="", segments=[], metrics=None, warnings=warnings,
                                   provider=ProviderInfo(stt_model=settings.stt_model, stt_ms=None, vad_ms=vad_ms))

    # moc theo tu cua STT; STT khong tra words (blaze-stt-1.0) thi dung doan VAD, cung cong thuc (spike 2026-11-25)
    timings = list(stt.word_timings) or [(s.start, s.end) for s in vad_segments]
    result_metrics, metric_warnings = compute_turn_metrics(
        stt.text, timings, form.question_audio_ended_at, form.recording_started_at, form.answer_limit_s,
        form.topic_id, settings)
    warnings += [w for w in metric_warnings if w not in warnings]
    if not stt.text:
        warnings.append("empty_transcript")
    metrics.AUDIO_SECONDS.inc(max(e for _, e in timings))
    log.info("transcribe_done bytes=%d audio_s=%.1f vad_ms=%d stt_ms=%d model=%s words=%d total_ms=%d", len(audio.data),
             max(e for _, e in timings), vad_ms, stt_ms or 0, stt.model, len(stt.word_timings),
             (time.perf_counter() - started) * 1000)
    return TranscriptionResult(
        no_speech=False, transcript=stt.text, segments=speech_spans(timings, settings.long_pause_s),
        metrics=result_metrics, warnings=warnings,
        provider=ProviderInfo(stt_model=stt.model, stt_ms=stt_ms, vad_ms=vad_ms))
