"""Bo do voice (spec 015 T027, quickstart §6): goi voice-service dang chay theo manifest, ghi bao cao markdown.

Clip `read`: STT 2 lan (co / khong keywords) -> loi am tiet, thuat ngu (SC-002), thoi gian (SC-001).
Clip `free`: STT 1 lan co keywords -> chi so trinh bay. TTS tren cau hoi golden -> byte dau (SC-003). Credit (SC-007).
Xuat evals/out/stt_samples.jsonl ({id, stt_of, noise: ["real_stt"], answer}) cho phan so diem cua AIE (SC-004) va
evals/out/raw.jsonl (moi lan goi, ghi ngay khi co).
Thoat 2: chua co clip nao. Thoat 1: service khong san sang / ma loi chi mang (sai token, het credit) -> khong ghi bao cao.

    cd apps/voice-service
    python -m evals.run_voice_eval --base-url http://localhost:8020 --out ../../specs/015-voice-mode/eval-results.md
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import httpx
from dotenv import dotenv_values

from .build_manifest import EVALS_DIR, GOLDEN, MANIFEST
from .eval_inputs import AUDIO_DIR, PHRASES_DIR, load_clips, load_phrases, load_pricing, tts_questions
from .eval_report import build_report
from .eval_runner import FatalServiceError, RawLog, evaluate_clips, measure_tts
from .eval_stats import latency_table, recognition_summary, session_credit, stt_credit
from .voice_eval_client import VoiceEvalClient

OUT_DIR = EVALS_DIR / "out"  # gitignore


def internal_token() -> str:
    """Token noi bo: bien moi truong, khong co thi apps/voice-service/.env (cung file service doc)."""
    return os.environ.get("VOICE_SERVICE_INTERNAL_TOKEN") or dotenv_values(EVALS_DIR.parent / ".env").get(
        "VOICE_SERVICE_INTERNAL_TOKEN") or ""


def run(args: argparse.Namespace, transport: Optional[httpx.BaseTransport] = None,
        ai_transport: Optional[httpx.BaseTransport] = None) -> int:
    # Moi kiem tra co the hong deu chay truoc khi goi mang: khong de ton credit roi moi loi
    all_clips = load_clips(args.manifest, args.golden, args.audio_dir)
    clips = [c for c in all_clips if c.audio is not None][: args.limit or None]
    missing = [c.clip_id for c in all_clips if c.audio is None]
    if not clips:
        print(f"Chua co file ghi am nao trong {args.audio_dir} (thieu {len(missing)} clip). Xem evals/README.md.")
        return 2
    if not args.out.parent.is_dir():
        print(f"Thu muc cua --out khong ton tai: {args.out.parent}")
        return 1
    pricing = load_pricing()
    questions = [] if args.skip_tts else tts_questions(args.golden, args.limit or 20)
    phrases = {t: load_phrases(t, args.ai_base_url, args.phrases_dir, ai_transport) for t in {c.track for c in clips}}
    log = RawLog(args.out_dir / "raw.jsonl")
    client = VoiceEvalClient(args.base_url, internal_token(), transport=transport)
    try:
        try:
            provider = client.health().get("provider")
        except httpx.HTTPError as exc:
            print(f"Khong goi duoc voice-service o {args.base_url} ({type(exc).__name__}): service dang chay chua?")
            return 1
        if provider != "blaze":
            print(f"voice-service bao provider={provider!r}: thieu BLAZE_API_KEY? Dung lai, khong do.")
            return 1
        res = evaluate_clips(client, clips, phrases, log)
        tts = None if args.skip_tts else measure_tts(client, questions, log)
    except FatalServiceError as exc:
        print(f"Dung do: voice-service tra `{exc}` (sai token / het credit / chua cau hinh). Ket qua da goi: {log.path}")
        return 1
    finally:
        client.close()
    data = {"date": dt.date.today().isoformat(), "stt_model": res["stt_model"], "clips_total": len(all_clips),
            "clips_found": len(all_clips) - len(missing), "clips_measured": len(clips), "missing": missing,
            "speakers": len({c.speaker for c in clips}), "keywords_sent": {t: len(p) for t, p in phrases.items()},
            "recognition": {"kw": recognition_summary(res["kw"]),
                            "kw_pair": recognition_summary([kw for kw, _ in res["pairs"]]),
                            "nokw_pair": recognition_summary([no for _, no in res["pairs"]])},
            "latency": latency_table(res["latency"], res["kw_failures"]), "kw_failures": res["kw_failures"],
            "tts": tts, "free": res["free"], "read_rows": res["read_rows"], "errors": res["errors"],
            "credit": {"stt_seconds": res["stt_seconds"], "stt_credit": stt_credit(res["stt_seconds"], pricing),
                       "session": session_credit(pricing)}}
    args.out.write_text(build_report(data), encoding="utf-8", newline="\n")
    samples = args.out_dir / "stt_samples.jsonl"
    samples.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in res["samples"]), encoding="utf-8",
                       newline="\n")
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
