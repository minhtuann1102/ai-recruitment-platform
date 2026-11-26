"""Vong do cua bo do voice (spec 015 T027): goi STT / TTS theo clip, cham, ghi tung ket qua ngay khi co.

- Moi lan goi ghi mot dong vao out/raw.jsonl ngay (ca ban ghi, gitignore): loi giua chung khong lam mat ket qua da ton
  credit, khong phai do lai.
- Ma loi chi mang (sai token, het credit, chua cau hinh) -> FatalServiceError: dung ngay, khong ghi bao cao.
- Do tre SC-001 chi tinh lan co keywords (ben goi that luon gui keywords), dem rieng lan loi.
- So co / khong keywords theo cap: chi clip ma ca hai che do deu thanh cong.
"""
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from app.transcript_tokens import tokens

from .eval_inputs import Clip
from .eval_stats import percentile
from .voice_eval_client import TranscribeResult, VoiceEvalClient
from .wer import edit_distance, term_recognition

FATAL_CODES = frozenset({"unauthorized", "quota_exceeded", "provider_unconfigured", "misconfigured"})


class FatalServiceError(RuntimeError):
    """Loi lam moi lan goi sau cung hong: dung do."""


class RawLog:
    """Ghi noi tiep tung ket qua vao jsonl (mo / dong moi lan de du lieu nam tren dia ngay)."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def write(self, record: Dict) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def score(clip: Clip, transcript: str, phrases: List[str]) -> Dict:
    ref = tokens(clip.reference)
    edits = edit_distance(ref, tokens(transcript))
    found, total = term_recognition(clip.reference, transcript, phrases)
    return {"ser": edits / len(ref), "edits": edits, "ref_tokens": len(ref), "terms_found": found, "terms_total": total}


def _transcribe(client: VoiceEvalClient, clip: Clip, mode: str, keywords: Optional[List[str]], log: RawLog,
                out: Dict) -> TranscribeResult:
    result = client.transcribe(clip.audio, keywords)
    log.write({"clip_id": clip.clip_id, "mode": mode, **asdict(result)})
    if result.error in FATAL_CODES:
        raise FatalServiceError(result.error)
    if not result.ok or result.no_speech:
        out["errors"].append((clip.clip_id, mode, result.error or "no_speech"))
        if mode == "kw":
            out["kw_failures"] += 0 if result.no_speech else 1
        return result
    out["stt_model"] = out["stt_model"] or result.stt_model
    out["stt_seconds"] += result.speech_end_s or 0.0
    if mode == "kw":
        out["latency"].append((result.speech_end_s, result.elapsed_s))
    return result


def evaluate_clips(client: VoiceEvalClient, clips: List[Clip], phrases: Dict[str, List[str]], log: RawLog) -> Dict:
    out = {"read_rows": [], "kw": [], "pairs": [], "latency": [], "kw_failures": 0, "free": [], "errors": [],
           "samples": [], "stt_seconds": 0.0, "stt_model": None}
    for clip in clips:
        kw = _transcribe(client, clip, "kw", phrases[clip.track], log, out)
        good = lambda r: r.ok and not r.no_speech  # noqa: E731
        if clip.kind == "free":
            if good(kw):
                out["free"].append({"clip_id": clip.clip_id, "speaker": clip.speaker, "track": clip.track,
                                    "metrics": kw.metrics, "warnings": kw.warnings})
            continue
        nokw = _transcribe(client, clip, "nokw", None, log, out)
        s_kw = score(clip, kw.transcript, phrases[clip.track]) if good(kw) else None
        s_no = score(clip, nokw.transcript, phrases[clip.track]) if good(nokw) else None
        if s_kw:
            out["kw"].append(s_kw)
            out["samples"].append({"id": f"{clip.clip_id}-stt", "stt_of": clip.golden_id, "noise": ["real_stt"],
                                   "answer": kw.transcript})
        if s_kw and s_no:
            out["pairs"].append((s_kw, s_no))
        terms = lambda s: f"{s['terms_found']}/{s['terms_total']}" if s else "–"  # noqa: E731
        out["read_rows"].append({"clip_id": clip.clip_id, "speaker": clip.speaker, "track": clip.track,
                                 "tier": clip.tier, "duration": kw.speech_end_s,
                                 "ser_kw": s_kw and s_kw["ser"], "ser_nokw": s_no and s_no["ser"],
                                 "terms_kw": terms(s_kw), "terms_nokw": terms(s_no),
                                 "elapsed_kw": kw.elapsed_s if s_kw else None})
    return out


def measure_tts(client: VoiceEvalClient, questions: List[str], log: RawLog) -> Dict:
    """Lan dau khong tinh (spike: lan noi dau doi khi ConnectError / cham)."""
    if questions:
        client.speak(questions[0])
    results = []
    for question in questions:
        result = client.speak(question)
        log.write({"tts_chars": len(question), **asdict(result)})
        if result.error in FATAL_CODES:
            raise FatalServiceError(result.error)
        results.append(result)
    firsts = [r.first_byte_s for r in results if r.ok and r.first_byte_s is not None]
    return {"n": len(results), "errors": sum(not r.ok for r in results), "p50": percentile(firsts, 50),
            "p95": percentile(firsts, 95), "total_p50": percentile([r.total_s for r in results if r.ok], 50)}
