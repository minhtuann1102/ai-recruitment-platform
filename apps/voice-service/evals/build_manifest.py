"""Dung evals/manifest.jsonl cho bo do voice (spec 015 T026, research R10) va in phieu doc cho nguoi ghi am.

Clip `read`: nguoi ghi doc `answer` cua mot mau golden Evaluator (apps/ai-service/evals/evaluator_golden.jsonl) ->
ban chuan co san. Chon co dinh (cung golden -> cung manifest):
- 4 track nhieu mau nhat (java, nodejs, python, ai_engineer), moi track 6 mau, 2 mau moi tier (strong / medium / weak)
  de lech band SC-004 co nghia va co ca cau ngan (weak ~5 s) lan cau dai (strong ~30-45 s) cho hai muc SC-001.
- Bo mau `adversarial` (khong bat ai doc cau tan cong prompt vao micro).
- Moi golden chi doc mot lan (moi `stt_of` mot ban STT); chia xen ke s1 / s2 -> moi nguoi 3 clip moi track.
- `ref_sha256` ghim van ban da doc: AIE sua `answer` sau khi ghi am thi bo do dung lai thay vi cham sai ban chuan.
Clip `free`: nguoi ghi tra loi tu do (khong co ban chuan), chi dung kiem chi so trinh bay.

KHONG sinh lai manifest sau khi da ghi am (r01.. se tro sang golden khac); lenh tu choi khi evals/audio/ co file.

Chay tu apps/voice-service:
    python -m evals.build_manifest              # ghi manifest.jsonl (khi chua ghi am)
    python -m evals.build_manifest --sheet s1   # in phieu doc cua nguoi ghi s1
"""
import argparse
import hashlib
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


def ref_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


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
                clips.append({"clip_id": f"r{len(clips) + 1:02d}", "golden_id": row["id"],
                              "ref_sha256": ref_hash(row["answer"]), "speaker": SPEAKERS[i], "kind": "read",
                              "track": track})
    for i in range(FREE_CLIPS):
        clips.append({"clip_id": f"f{i + 1:02d}", "speaker": SPEAKERS[i % len(SPEAKERS)], "kind": "free",
                      "track": READ_TRACKS[i % len(READ_TRACKS)]})
    return clips


def free_prompts(clips: List[Dict], golden: List[Dict]) -> Dict[str, str]:
    """Cau hoi goi y cho tung clip free: khong lap cau da dung, tranh cau ma chinh nguoi ghi vua doc dap an mau, roi
    uu tien cau chua co ai doc."""
    qid_of = {r["id"]: r["qid"] for r in golden}
    read_by = {}  # qid -> nguoi da doc dap an mau cua cau do
    for c in clips:
        if c.get("golden_id") in qid_of:
            read_by.setdefault(qid_of[c["golden_id"]], set()).add(c["speaker"])
    prompts, used = {}, set()
    for c in (c for c in clips if c["kind"] == "free"):
        rows = sorted((r for r in golden if r.get("track") == c["track"] and r["question"] not in used),
                      key=lambda r: (c["speaker"] in read_by.get(r["qid"], ()), r["qid"] in read_by, r["id"]))
        prompts[c["clip_id"]] = rows[0]["question"] if rows else ""
        used.add(prompts[c["clip_id"]])
    return prompts


def write_manifest(clips: List[Dict], path: Path = MANIFEST) -> None:
    path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in clips), encoding="utf-8", newline="\n")


def reading_sheet(clips: List[Dict], golden: List[Dict], speaker: str) -> str:
    """Phieu cho mot nguoi ghi: ten file can luu + van ban can doc (read) hoac cau hoi goi y (free)."""
    by_id = {r["id"]: r for r in golden}
    prompts = free_prompts(clips, golden)
    lines = [f"# Phieu ghi am cua {speaker}", ""]
    for c in clips:
        if c["speaker"] != speaker:
            continue
        lines.append(f"## {c['clip_id']} ({c['kind']}, {c['track']}) -> luu thanh evals/audio/{c['clip_id']}.webm")
        if c["kind"] == "read":
            lines += [f"Cau hoi: {by_id[c['golden_id']]['question']}", "Doc nguyen van:", by_id[c["golden_id"]]["answer"]]
        else:
            lines += [f"Tra loi tu do (30-90 giay) cau: {prompts[c['clip_id']]}"]
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", choices=SPEAKERS, help="in phieu doc cua nguoi ghi thay vi ghi manifest")
    parser.add_argument("--force", action="store_true", help="ghi de manifest du evals/audio/ da co file")
    args = parser.parse_args()
    golden = load_golden()
    if args.sheet:
        sys.stdout.reconfigure(encoding="utf-8")  # console Windows (cp1252) khong in duoc tieng Viet
        with MANIFEST.open(encoding="utf-8") as f:  # phieu theo manifest da commit, khong theo golden hien tai
            print(reading_sheet([json.loads(line) for line in f if line.strip()], golden, args.sheet))
        return
    audio = EVALS_DIR / "audio"
    if not args.force and audio.is_dir() and any(audio.iterdir()):
        sys.exit("evals/audio/ da co file ghi am: sinh lai manifest se lam lech clip va ban chuan. Dung --force neu chac.")
    clips = build(golden)
    write_manifest(clips)
    print(f"{MANIFEST.name}: {len(clips)} clip")


if __name__ == "__main__":
    main()
