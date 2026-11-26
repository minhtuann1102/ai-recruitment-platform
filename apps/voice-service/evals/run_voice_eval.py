"""Bo do voice (spec 015 T027, quickstart §6): goi voice-service dang chay theo manifest, ghi bao cao markdown.

Clip `read`: STT 2 lan (co / khong keywords) -> loi am tiet, thuat ngu (SC-002), thoi gian (SC-001).
Clip `free`: STT 1 lan co keywords -> chi so trinh bay. TTS tren cau hoi golden -> byte dau (SC-003). Credit (SC-007).
Xuat them evals/out/stt_samples.jsonl ({id, stt_of, noise: ["real_stt"], answer}) cho phan so diem cua AIE (SC-004).
Chua co clip nao trong evals/audio/ -> in danh sach thieu, thoat 2, khong ghi bao cao.

    cd apps/voice-service
    python -m evals.run_voice_eval --base-url http://localhost:8020 --out ../../specs/015-voice-mode/eval-results.md
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from dotenv import dotenv_values

from .build_manifest import EVALS_DIR, GOLDEN, MANIFEST
from .eval_inputs import AUDIO_DIR, PHRASES_DIR, Clip, load_clips, load_phrases, load_pricing, tts_questions
from .eval_report import build_report
from .eval_stats import latency_table, percentile, recognition_summary, session_credit, stt_credit
from .voice_eval_client import VoiceEvalClient
from .wer import syllable_error_rate, term_recognition

OUT_DIR = EVALS_DIR / "out"  # gitignore


def internal_token() -> str:
    """Token noi bo: bien moi truong, khong co thi apps/voice-service/.env (cung file service doc)."""
    return os.environ.get("VOICE_SERVICE_INTERNAL_TOKEN") or dotenv_values(EVALS_DIR.parent / ".env").get(
        "VOICE_SERVICE_INTERNAL_TOKEN") or ""


def _score(clip: Clip, transcript: str, phrases: List[str]) -> Dict:
    found, total = term_recognition(clip.reference, transcript, phrases)
    return {"ser": syllable_error_rate(clip.reference, transcript), "terms_found": found, "terms_total": total}


def evaluate_clips(client: VoiceEvalClient, clips: List[Clip], phrases: Dict[str, List[str]]) -> Dict:
    out = {"read_rows": [], "kw": [], "nokw": [], "latency": [], "free": [], "errors": [], "samples": [],
           "stt_seconds": 0.0, "stt_model": None}
    for clip in clips:
        modes = (("kw", phrases[clip.track]), ("nokw", None)) if clip.kind == "read" else (("kw", phrases[clip.track]),)
        runs = {}
        for mode, keywords in modes:
            result = client.transcribe(clip.audio, keywords)
            runs[mode] = result
            if not result.ok or result.no_speech:
                out["errors"].append((clip.clip_id, mode, result.error or "no_speech"))
                continue
            out["stt_model"] = out["stt_model"] or result.stt_model
            out["stt_seconds"] += result.speech_end_s or 0.0
            out["latency"].append((result.speech_end_s, result.elapsed_s))
        kw = runs["kw"]
        if clip.kind == "free":
            if kw.ok and not kw.no_speech:
                out["free"].append({"clip_id": clip.clip_id, "speaker": clip.speaker, "track": clip.track,
                                    "metrics": kw.metrics, "warnings": kw.warnings})
            continue
        scores = {m: _score(clip, r.transcript, phrases[clip.track]) for m, r in runs.items() if r.ok and not r.no_speech}
        for mode, score in scores.items():
            out[mode].append(score)
        if "kw" in scores:
            out["samples"].append({"id": f"{clip.clip_id}-stt", "stt_of": clip.golden_id, "noise": ["real_stt"],
                                   "answer": kw.transcript})
        terms = {m: f"{scores[m]['terms_found']}/{scores[m]['terms_total']}" if m in scores else "–"
                 for m in ("kw", "nokw")}
        out["read_rows"].append({"clip_id": clip.clip_id, "speaker": clip.speaker, "track": clip.track,
                                 "tier": clip.tier, "duration": kw.speech_end_s,
                                 "ser_kw": scores.get("kw", {}).get("ser"), "ser_nokw": scores.get("nokw", {}).get("ser"),
                                 "terms_kw": terms["kw"], "terms_nokw": terms["nokw"],
                                 "elapsed_kw": kw.elapsed_s if "kw" in scores else None})
    return out


def measure_tts(client: VoiceEvalClient, questions: List[str]) -> Dict:
    """Lan dau khong tinh (spike: lan noi dau doi khi ConnectError / cham)."""
    if questions:
        client.speak(questions[0])
    results = [client.speak(q) for q in questions]
    firsts = [r.first_byte_s for r in results if r.ok and r.first_byte_s is not None]
    return {"n": len(results), "errors": sum(not r.ok for r in results), "p50": percentile(firsts, 50),
            "p95": percentile(firsts, 95), "total_p50": percentile([r.total_s for r in results if r.ok], 50)}


def run(args: argparse.Namespace, transport: Optional[httpx.BaseTransport] = None,
        ai_transport: Optional[httpx.BaseTransport] = None) -> int:
    all_clips = load_clips(args.manifest, args.golden, args.audio_dir)
    clips = [c for c in all_clips if c.audio is not None][: args.limit or None]
    missing = [c.clip_id for c in all_clips if c.audio is None]
    if not clips:
        print(f"Chua co file ghi am nao trong {args.audio_dir} (thieu {len(missing)} clip). Xem evals/README.md.")
        return 2
    phrases = {t: load_phrases(t, args.ai_base_url, args.phrases_dir, ai_transport) for t in {c.track for c in clips}}
    client = VoiceEvalClient(args.base_url, internal_token(), transport=transport)
    try:
        provider = client.health().get("provider")
        if provider != "blaze":
            print(f"voice-service bao provider={provider!r}: thieu BLAZE_API_KEY? Dung lai, khong do.")
            return 1
        res = evaluate_clips(client, clips, phrases)
        tts = None if args.skip_tts else measure_tts(client, tts_questions(args.golden, args.limit or 20))
    finally:
        client.close()
    pricing = load_pricing()
    data = {"date": dt.date.today().isoformat(), "stt_model": res["stt_model"], "clips_total": len(all_clips),
            "clips_found": len(all_clips) - len(missing), "missing": missing,
            "speakers": len({c.speaker for c in clips}), "keywords_sent": {t: len(p) for t, p in phrases.items()},
            "recognition": {"kw": recognition_summary(res["kw"]), "nokw": recognition_summary(res["nokw"])},
            "latency": latency_table(res["latency"]), "tts": tts, "free": res["free"], "read_rows": res["read_rows"],
            "errors": res["errors"], "credit": {"stt_seconds": res["stt_seconds"],
                                                "stt_credit": stt_credit(res["stt_seconds"], pricing),
                                                "session": session_credit(pricing)}}
    args.out.write_text(build_report(data), encoding="utf-8", newline="\n")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    samples = args.out_dir / "stt_samples.jsonl"
    samples.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in res["samples"]), encoding="utf-8")
    print(f"Da do {len(clips)} clip (thieu {len(missing)}), loi {len(res['errors'])}. Bao cao: {args.out}; mau STT: {samples}")
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base-url", default="http://localhost:8020", help="voice-service dang chay")
    p.add_argument("--ai-base-url", default="http://localhost:8000", help="ai-service, chi khi chua co cache thuat ngu")
    p.add_argument("--out", type=Path, required=True, help="file markdown bao cao")
    p.add_argument("--limit", type=int, default=0, help="chi do N clip dau (va N cau TTS) de tiet kiem credit")
    p.add_argument("--skip-tts", action="store_true")
    p.add_argument("--manifest", type=Path, default=MANIFEST)
    p.add_argument("--golden", type=Path, default=GOLDEN)
    p.add_argument("--audio-dir", type=Path, default=AUDIO_DIR)
    p.add_argument("--phrases-dir", type=Path, default=PHRASES_DIR)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(run(parse_args()))
