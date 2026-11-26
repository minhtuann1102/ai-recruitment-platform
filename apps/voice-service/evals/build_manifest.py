"""Dung evals/manifest.jsonl cho bo do voice (spec 015 T026, research R10) va in phieu doc cho nguoi ghi am.

Clip `read`: nguoi ghi doc `answer` cua mot mau golden Evaluator (apps/ai-service/evals/evaluator_golden.jsonl) ->
ban chuan co san. Chon co dinh (cung golden -> cung manifest):
- 4 track nhieu mau nhat (java, nodejs, python, ai_engineer), moi track 6 mau, 2 mau moi tier (strong / medium / weak)
  de lech band SC-004 co nghia va co ca cau ngan (weak ~5 s) lan cau dai (strong ~30-45 s) cho hai muc SC-001.
- Bo mau `adversarial` (khong bat ai doc cau tan cong prompt vao micro).
- Moi golden chi doc mot lan (moi `stt_of` mot ban STT); chia xen ke s1 / s2 -> moi nguoi 3 clip moi track.
Clip `free`: nguoi ghi tra loi tu do (khong co ban chuan), chi dung kiem chi so trinh bay.

Chay tu apps/voice-service:
    python -m evals.build_manifest              # ghi lai manifest.jsonl
    python -m evals.build_manifest --sheet s1   # in phieu doc cua nguoi ghi s1
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

EVALS_DIR = Path(__file__).resolve().parent
MANIFEST = EVALS_DIR / "manifest.jsonl"
GOLDEN = EVALS_DIR.parents[1] / "ai-service" / "evals" / "evaluator_golden.jsonl"
READ_TRACKS = ("java_backend", "nodejs_backend", "python_backend", "ai_engineer")
TIERS = ("strong", "medium", "weak")
PER_TIER = 2
SPEAKERS = ("s1", "s2")
FREE_CLIPS = 6


def load_golden(path: Path = GOLDEN) -> List[Dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build(golden: List[Dict]) -> List[Dict]:
    """Danh sach clip theo thu tu ghi: 24 `read` (r01..r24) roi 6 `free` (f01..f06)."""
    clips: List[Dict] = []
    for track in READ_TRACKS:
        for tier in TIERS:
            rows = sorted((r for r in golden if r.get("track") == track and r.get("intended_tier") == tier
                           and not r.get("adversarial")), key=lambda r: r["id"])
            if len(rows) < PER_TIER:
                raise ValueError(f"{track}/{tier}: chi co {len(rows)} mau golden, can {PER_TIER}")
            for i, row in enumerate(rows[:PER_TIER]):
                clips.append({"clip_id": f"r{len(clips) + 1:02d}", "golden_id": row["id"], "speaker": SPEAKERS[i],
                              "kind": "read", "track": track})
    for i in range(FREE_CLIPS):
        clips.append({"clip_id": f"f{i + 1:02d}", "speaker": SPEAKERS[i % len(SPEAKERS)], "kind": "free",
                      "track": READ_TRACKS[i % len(READ_TRACKS)]})
    return clips


def write_manifest(clips: List[Dict], path: Path = MANIFEST) -> None:
    path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in clips), encoding="utf-8", newline="\n")


def reading_sheet(clips: List[Dict], golden: List[Dict], speaker: str) -> str:
    """Phieu cho mot nguoi ghi: ten file can luu + van ban can doc (read) hoac cau hoi goi y (free)."""
    by_id = {r["id"]: r for r in golden}
    questions = {}  # track -> cau hoi dau tien cua track (goi y cho clip free)
    for r in sorted(golden, key=lambda r: r["id"]):
        questions.setdefault(r.get("track"), r["question"])
    lines = [f"# Phieu ghi am cua {speaker}", ""]
    for c in clips:
        if c["speaker"] != speaker:
            continue
        lines.append(f"## {c['clip_id']} ({c['kind']}, {c['track']}) -> luu thanh evals/audio/{c['clip_id']}.webm")
        if c["kind"] == "read":
            lines += [f"Cau hoi: {by_id[c['golden_id']]['question']}", "Doc nguyen van:", by_id[c["golden_id"]]["answer"]]
        else:
            lines += [f"Tra loi tu do (30-90 giay), vi du cau: {questions.get(c['track'], '')}"]
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", choices=SPEAKERS, help="in phieu doc cua nguoi ghi thay vi ghi manifest")
    args = parser.parse_args()
    golden = load_golden()
    clips = build(golden)
    if args.sheet:
        sys.stdout.reconfigure(encoding="utf-8")  # console Windows (cp1252) khong in duoc tieng Viet
        print(reading_sheet(clips, golden, args.sheet))
        return
    write_manifest(clips)
    print(f"{MANIFEST.name}: {len(clips)} clip")


if __name__ == "__main__":
    main()
