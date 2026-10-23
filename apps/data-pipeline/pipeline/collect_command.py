"""Lenh collect: tai Q&A tu cac repo GitHub trong crawlers/qa_sources.py -> data/raw/collected_qa/.

Moi nguon mot file JSONL; ban ghi tho chua dich, chua gan topic (buoc enrich lam sau).
Lam sach + xoa PII ngay khi thu thap (constitution V). Noi dung KHONG commit (repo public).
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from typing import Dict, List

import httpx

from crawlers.github_raw_client import GithubRawClient, blob_url
from crawlers.qa_sources import SOURCES, QASource

from .pii_patterns import scrub_pii
from .settings import RAW_DIR
from .text_cleaning import clean_text

COLLECTED_DIR = RAW_DIR / "collected_qa"
MIN_QUESTION_CHARS = 10
MIN_ANSWER_CHARS = 30
# Dap an mau qua dai lam loang embedding va de vuot gioi han token khi embed qa_pair
MAX_ANSWER_CHARS = 4000


def truncate_answer(answer: str, limit: int = MAX_ANSWER_CHARS):
    """Cat o cho xuong doan gan nhat truoc limit; dong code fence neu dang mo. Tra (text, da_cat)."""
    if len(answer) <= limit:
        return answer, False
    cut = answer.rfind("\n\n", 0, limit)
    text = answer[: cut if cut > limit // 2 else limit].rstrip()
    if text.count("```") % 2:
        text += "\n```"
    return text, True


def collected_id(source: str, url: str, question: str) -> str:
    """cid on dinh theo nguon: doi cau hoi o upstream thi thanh cap moi (khac de-qa-NNNN)."""
    digest = hashlib.md5(f"{url}\n{question}".encode("utf-8")).hexdigest()[:8]
    return f"cr-{source}-{digest}"


def records_from_markdown(source: QASource, path: str, markdown: str, collected_at: str) -> List[Dict]:
    url = blob_url(source.repo, path)
    records = []
    for raw_question, raw_answer in source.parse(markdown):
        question = scrub_pii(clean_text(raw_question))
        answer = scrub_pii(clean_text(raw_answer))
        if len(question) < MIN_QUESTION_CHARS or len(answer) < MIN_ANSWER_CHARS:
            continue
        answer, truncated = truncate_answer(answer)
        records.append(
            {
                "cid": collected_id(source.name, url, question),
                "source": source.name,
                "source_url": url,
                "question": question,
                "answer": answer,
                "truncated": truncated,
                "lang": source.lang,
                "license": source.license,
                "attribution": source.attribution,
                "collected_at": collected_at,
            }
        )
    return records


def _expand_paths(client: GithubRawClient, source: QASource, failures: List[str]) -> List[str]:
    """'thu-muc/*.md' -> cac file .md trong thu muc; duong dan file giu nguyen."""
    paths: List[str] = []
    for path in source.paths:
        if not path.endswith("/*.md"):
            paths.append(path)
            continue
        try:
            paths.extend(client.list_markdown(source.repo, path[: -len("/*.md")]))
        except httpx.HTTPError as exc:
            failures.append(f"{source.repo}/{path}: {exc}")
    return paths


def run_collect(args: argparse.Namespace) -> int:
    selected = [s for s in SOURCES if not args.only or s.name in args.only]
    client = GithubRawClient(delay=args.delay)
    collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    COLLECTED_DIR.mkdir(parents=True, exist_ok=True)
    totals, failures = {}, []
    try:
        for source in selected:
            records: List[Dict] = []
            for path in _expand_paths(client, source, failures):
                try:
                    markdown = client.fetch(source.repo, path)
                except httpx.HTTPError as exc:
                    failures.append(f"{source.repo}/{path}: {exc}")
                    continue
                records.extend(records_from_markdown(source, path, markdown, collected_at))
            unique = list({r["cid"]: r for r in records}.values())
            out = COLLECTED_DIR / f"{source.name}.jsonl"
            out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in unique), encoding="utf-8")
            totals[source.name] = len(unique)
            print(f"{source.name:<28} {len(unique):>5} cap")
    finally:
        client.close()
    for failure in failures:
        print(f"[loi] {failure}", file=sys.stderr)
    print(f"== tong {sum(totals.values())} cap tu {len(totals)} nguon -> {COLLECTED_DIR}")
    empty = [name for name, count in totals.items() if count == 0]
    if empty:
        print(f"[loi] nguon thu 0 cap (doi cau truc?): {', '.join(empty)}", file=sys.stderr)  # FR-025
    return 1 if failures or empty else 0
