"""Dau vao cua bo do voice (spec 015 T027): manifest, mau golden, file ghi am, danh sach thuat ngu theo track.

Thuat ngu lay tu cache `evals/phrases/<track>.json` (commit, ghi ngay + commit ai-service da sinh); chua co cache thi goi
GET /api/stt/phrases?track= cua ai-service roi luu cache. Ca hai cach cho cung danh sach ma ben goi that se gui.
"""
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from .build_manifest import EVALS_DIR, GOLDEN, MANIFEST, load_golden

AUDIO_DIR = EVALS_DIR / "audio"  # gitignore (FR-023)
PHRASES_DIR = EVALS_DIR / "phrases"
PRICING = EVALS_DIR / "pricing.json"
AUDIO_TYPES = {".webm": "audio/webm", ".ogg": "audio/ogg", ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4"}
TTS_MAX_CHARS = 300  # SC-003 do voi cau hoi <= 300 ky tu


@dataclass(frozen=True)
class Clip:
    clip_id: str
    speaker: str
    kind: str  # read | free
    track: str
    golden_id: Optional[str] = None
    reference: Optional[str] = None  # `answer` cua mau golden (clip read)
    tier: Optional[str] = None
    audio: Optional[Path] = None  # None = chua ghi


def find_audio(clip_id: str, audio_dir: Path) -> Optional[Path]:
    for ext in AUDIO_TYPES:
        path = audio_dir / f"{clip_id}{ext}"
        if path.is_file():
            return path
    return None


def load_clips(manifest: Path = MANIFEST, golden_path: Path = GOLDEN, audio_dir: Path = AUDIO_DIR) -> List[Clip]:
    """Clip theo thu tu manifest; clip read tro toi golden khong ton tai -> ValueError (manifest hong)."""
    by_id = {r["id"]: r for r in load_golden(golden_path)}
    clips = []
    with manifest.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            gold = None
            if row["kind"] == "read":
                gold = by_id.get(row.get("golden_id"))
                if gold is None:
                    raise ValueError(f"{row['clip_id']}: golden_id {row.get('golden_id')!r} khong co trong golden")
            clips.append(Clip(clip_id=row["clip_id"], speaker=row["speaker"], kind=row["kind"], track=row["track"],
                              golden_id=row.get("golden_id"), reference=gold["answer"] if gold else None,
                              tier=gold.get("intended_tier") if gold else None,
                              audio=find_audio(row["clip_id"], audio_dir)))
    return clips


def tts_questions(golden_path: Path = GOLDEN, limit: int = 20) -> List[str]:
    """`limit` cau hoi golden khac nhau, <= TTS_MAX_CHARS, theo thu tu id (co dinh giua cac lan chay)."""
    seen: List[str] = []
    for row in sorted(load_golden(golden_path), key=lambda r: r["id"]):
        question = row["question"].strip()
        if question and len(question) <= TTS_MAX_CHARS and question not in seen:
            seen.append(question)
    return seen[:limit]


def load_phrases(track: str, ai_base_url: str, phrases_dir: Path = PHRASES_DIR,
                 transport: Optional[httpx.BaseTransport] = None) -> List[str]:
    """Danh sach thuat ngu cua track: cache neu co, khong thi hoi ai-service va ghi cache."""
    cache = phrases_dir / f"{track}.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))["phrases"]
    with httpx.Client(base_url=ai_base_url, transport=transport, timeout=10) as client:
        response = client.get("/api/stt/phrases", params={"track": track})
        response.raise_for_status()
        phrases = response.json()["phrases"]
    phrases_dir.mkdir(parents=True, exist_ok=True)
    payload = {"track": track, "source": f"GET {ai_base_url}/api/stt/phrases", "ai_service_commit": None,
               "generated_at": dt.date.today().isoformat(), "phrases": phrases}
    cache.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return phrases


def load_pricing(path: Path = PRICING) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))
