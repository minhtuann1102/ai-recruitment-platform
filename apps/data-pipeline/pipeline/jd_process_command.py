"""Lenh process-jd (spec 009 US2, contracts/pipeline-cli-jd.md): raw (crawl + synthetic) -> JD chuan hoa + chunk + bao cao.

Offline: khong DB, khong key (FR-014). Doc moi data/raw/jd/**/*.jsonl -> jd_normalized.jsonl, jd_chunks.jsonl
(sap theo jd_id, khoa JSON sap, newline '\\n': cung input -> file giong het tung byte) + bao cao in man hinh va ghi
data/processed/jd-report-<UTC ts>.json. Chunk trung content_hash chi giu ban dau (FR-013).
Ma thoat: 0; 1 khong doc duoc raw / danh muc ky nang, hoac con PII trong output (khi do khong ghi output JD).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from .jd_process_report import build_report, count_output_pii, print_report
from .jd_record_dedup import build_records
from .jd_sections import build_chunks
from .settings import JD_CHUNKS_PATH, JD_NORMALIZED_PATH, JD_RAW_DIR, PROCESSED_DIR, SKILL_DICTIONARY_PATH
from .skill_dictionary import SkillDictionaryError, load_skill_dictionary

EXIT_OK = 0
EXIT_INPUT_ERROR = 1


class RawReadError(RuntimeError):
    pass


def read_raw_records(raw_dir: Path) -> List[Dict]:
    """Moi dong JSON cua moi file *.jsonl duoi raw_dir (ca synthetic/), theo thu tu duong dan."""
    files = sorted(raw_dir.rglob("*.jsonl"), key=lambda p: p.relative_to(raw_dir).as_posix())
    if not files:
        raise RawReadError(f"khong co file raw *.jsonl trong {raw_dir} (chay crawl-jd truoc)")
    records = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise RawReadError(f"khong doc duoc {path}: {exc}") from exc
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise RawReadError(f"{path}:{number}: JSON loi ({exc})") from exc
            if not isinstance(record, dict):
                raise RawReadError(f"{path}:{number}: moi dong phai la mot object")
            records.append(record)
    return records


def unique_chunks(records: Iterable[Dict]) -> List[Dict]:
    seen, chunks = set(), []
    for record in records:
        for chunk in build_chunks(record):
            if chunk["content_hash"] not in seen:
                seen.add(chunk["content_hash"])
                chunks.append(chunk)
    return chunks


def write_jsonl(path: Path, rows: Iterable[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(body, encoding="utf-8", newline="\n")


def write_report(report: Dict, out_dir: Path, now: datetime) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"jd-report-{now:%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def run_process_jd(args: argparse.Namespace) -> int:
    try:
        dictionary = load_skill_dictionary(SKILL_DICTIONARY_PATH)
        raws = read_raw_records(JD_RAW_DIR)
    except (SkillDictionaryError, RawReadError) as exc:
        print(f"[loi] {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    result = build_records(raws, dictionary)
    chunks = unique_chunks(result.records)
    pii_remaining = count_output_pii(result.records, chunks)
    report = build_report(raws, result, chunks, pii_remaining)
    print_report(report)
    if pii_remaining:
        print(f"[loi] con {pii_remaining} PII trong output: khong ghi file JD (FR-009)", file=sys.stderr)
    else:
        write_jsonl(JD_NORMALIZED_PATH, result.records)
        write_jsonl(JD_CHUNKS_PATH, chunks)
        print(f"-> {JD_NORMALIZED_PATH}\n-> {JD_CHUNKS_PATH}")
    print(f"-> {write_report(report, PROCESSED_DIR, datetime.now(timezone.utc))}")
    return EXIT_INPUT_ERROR if pii_remaining else EXIT_OK
