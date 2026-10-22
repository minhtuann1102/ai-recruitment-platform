"""Prepare a review batch of interview Q&A seed pairs with mechanical checks (no model judgement).

Checks per pair: token estimate of the qa_pair chunk against the ai-service budgets, catalog topic and levels,
hard-pair count of the topic (curated seeds + processed crawl) and whether dropping the pair breaks SC-001,
golden-set labels that point at it, and optionally each grounding URL's status and the key terms its page contains.

Usage:
  python prepare_review_batch.py --track frontend --catalog apps/ai-service/app/catalog --out batch.json
  python prepare_review_batch.py --ids de-qa-1250..1262,de-qa-1300 --check-urls --out batch.json
"""
import argparse
import html
import json
import math
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

CHARS_PER_TOKEN = 3            # same estimate as estimate_tokens() in apps/ai-service/app/rag/retriever.py
PLAN_SNIPPET_BUDGET = 600      # Planner reference snippets per topic (FR-AI-022)
RETRIEVE_BUDGET = 1500         # default retriever token budget
HARD_FLOOR = 2                 # SC-001: each middle/senior topic needs >= 2 hard pairs
SENIOR_LEVELS = {"middle", "senior"}
USER_AGENT = "ai-recruit-qa-review/0.1 (+https://github.com/minhtuann1102/ai-recruitment-platform)"
RANGE_RE = re.compile(r"^de-qa-(\d{4})\.\.(?:de-qa-)?(\d{4})$")


def parse_ids(spec):
    """'de-qa-1250..1252,de-qa-1300' -> {'de-qa-1250', 'de-qa-1251', 'de-qa-1252', 'de-qa-1300'}."""
    ids = set()
    for part in filter(None, (p.strip() for p in spec.split(","))):
        match = RANGE_RE.match(part)
        if match:
            ids.update(f"de-qa-{n:04d}" for n in range(int(match.group(1)), int(match.group(2)) + 1))
        elif re.match(r"^de-qa-\d{4}$", part):
            ids.add(part)
        else:
            raise ValueError(f"invalid id: {part}")
    return ids


def estimate_tokens(text):
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def load_catalog(dirs):
    topics = {}
    for directory in dirs:
        for path in sorted(Path(directory).glob("*.yaml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for topic in doc.get("topics", []):
                topics[topic["id"]] = dict(topic, track=doc.get("track", path.stem))
    return topics


def load_seed_pairs(seeds_dir):
    pairs = []
    for path in sorted(Path(seeds_dir).glob("*.json")):
        for pair in json.loads(path.read_text(encoding="utf-8")):
            if isinstance(pair, dict) and pair.get("qa_id"):
                pairs.append(dict(pair, _file=path.name))
    return pairs


def crawl_hard_counts(processed_jsonl):
    """Hard qa_pair records per topic from datasets other than the curated seed (already counted from files)."""
    counts = Counter()
    path = Path(processed_jsonl)
    if not path.exists():
        return counts, False
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        meta = record.get("metadata", {})
        if (record.get("difficulty") == "hard" and meta.get("chunk_type") == "qa_pair"
                and meta.get("dataset") != "de_interview_qa"):
            counts[record.get("topic_id")] += 1
    return counts, True


def load_golden(path):
    labels = defaultdict(list)
    if not path:
        return labels
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    for query in doc if isinstance(doc, list) else doc.get("queries", []):
        for qa_id in query.get("relevant") or query.get("expected_qa_ids") or []:
            labels[qa_id].append(query.get("id"))
    return labels


def key_terms(pair):
    """Terms a supporting page should mention: tags plus short inline-code spans from the answer."""
    terms = [t.replace("-", " ") for t in pair.get("tags", [])]
    terms += [m for m in re.findall(r"`([^`\n]{3,40})`", pair.get("answer", "")) if not m.startswith("http")]
    seen, out = set(), []
    for term in terms:
        if term.lower() not in seen:
            seen.add(term.lower())
            out.append(term)
    return out[:15]


def check_url(url, terms, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(3_000_000).decode("utf-8", errors="replace")
            status, final_url = response.status, response.geturl()
    except Exception as exc:  # network errors are data for the reviewer, not a reason to stop
        return {"url": url, "status": f"error: {type(exc).__name__}: {exc}"[:200]}
    text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", body))).lower()
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
    found = [t for t in terms if t.lower() in text]
    return {"url": url, "status": status, "final_url": final_url,
            "title": html.unescape(title.group(1)).strip()[:120] if title else "",
            "terms_found": found, "terms_missing": [t for t in terms if t not in found]}


def sub_question_hint(question):
    """Rough count of asks: question marks plus items in a trailing 'a, b, c và d' list."""
    tail = question.rsplit(":", 1)[-1]
    listed = len(re.split(r",|\bvà\b|\band\b", tail)) if ":" in question else 1
    return max(question.count("?"), 1, listed)


def build_batch(args):
    topics = load_catalog(args.catalog)
    seed_pairs = load_seed_pairs(args.seeds)
    crawl_hard, crawl_found = crawl_hard_counts(args.processed)
    curated_hard = Counter(p["topic_id"] for p in seed_pairs if p.get("difficulty") == "hard")
    golden = load_golden(args.golden)

    if args.ids:
        wanted = parse_ids(args.ids)
        selected = [p for p in seed_pairs if p["qa_id"] in wanted]
    else:
        selected = [p for p in seed_pairs if p["_file"] == f"hard-{args.track}.json"]
    for extra in args.extra:
        selected += [dict(p, _file=p.get("_file", Path(extra).name))
                     for p in json.loads(Path(extra).read_text(encoding="utf-8"))]
    if not selected:
        sys.exit("no pairs selected: check --track / --ids and --seeds")

    out = []
    for pair in sorted(selected, key=lambda p: p["qa_id"]):
        topic = topics.get(pair["topic_id"])
        levels = topic.get("levels", []) if topic else []
        hard_total = curated_hard[pair["topic_id"]] + crawl_hard[pair["topic_id"]]
        chunk_tokens = estimate_tokens(f"{pair['question']}\n\n{pair['answer']}")
        checks = {
            "chunk_tokens_est": chunk_tokens,
            "over_plan_budget": chunk_tokens > PLAN_SNIPPET_BUDGET,
            "over_retrieve_budget": chunk_tokens > RETRIEVE_BUDGET,
            "topic_in_catalog": topic is not None,
            "topic_levels_ok": bool(SENIOR_LEVELS & set(levels)),
            "topic_hard_total": hard_total,
            "topic_hard_curated": curated_hard[pair["topic_id"]],
            "drop_breaks_sc001": bool(SENIOR_LEVELS & set(levels)) and hard_total - 1 < HARD_FLOOR,
            "golden_labels": golden.get(pair["qa_id"], []),
            "sub_questions_hint": sub_question_hint(pair["question"]),
            "already_reviewed_by": pair.get("reviewed_by") or "",
        }
        if args.check_urls:
            terms = key_terms(pair)
            checks["urls"] = []
            for url in pair.get("grounding_urls", []):
                checks["urls"].append(check_url(url, terms, args.timeout))
                time.sleep(args.delay)
        out.append({
            "qa_id": pair["qa_id"], "file": pair["_file"], "topic_id": pair["topic_id"],
            "topic": {k: topic.get(k) for k in ("title", "levels", "key_concepts", "category", "track")} if topic else None,
            "difficulty": pair.get("difficulty"), "question": pair["question"], "answer": pair["answer"],
            "tags": pair.get("tags", []), "grounding_urls": pair.get("grounding_urls", []), "checks": checks,
        })
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "selection": args.ids or args.track, "crawl_counts_included": crawl_found, "pairs": out}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    pick = parser.add_mutually_exclusive_group(required=True)
    pick.add_argument("--track", help="frontend | java | nodejs | python | devops | ai (reads hard-<track>.json)")
    pick.add_argument("--ids", help="e.g. de-qa-1250..1262,de-qa-1300")
    parser.add_argument("--seeds", default="apps/data-pipeline/data/seeds/interview_qa")
    parser.add_argument("--catalog", action="append", default=[], help="catalog dir with *.yaml (repeatable)")
    parser.add_argument("--processed", default="apps/data-pipeline/data/processed/interview_qa.jsonl")
    parser.add_argument("--golden", help="golden set JSON (queries with 'relevant' qa_ids)")
    parser.add_argument("--extra", action="append", default=[], help="extra pairs JSON appended to the batch")
    parser.add_argument("--check-urls", action="store_true")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not args.catalog:
        args.catalog = ["apps/ai-service/app/catalog"]

    batch = build_batch(args)
    Path(args.out).write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(batch['pairs'])} pairs -> {args.out} (crawl hard counts included: {batch['crawl_counts_included']})")
    for p in batch["pairs"]:
        c = p["checks"]
        flags = [name for name, on in (("over600", c["over_plan_budget"]), ("over1500", c["over_retrieve_budget"]),
                                       ("no-topic", not c["topic_in_catalog"]), ("bad-level", not c["topic_levels_ok"]),
                                       ("drop-breaks-SC001", c["drop_breaks_sc001"]), ("golden", c["golden_labels"]))
                 if on]
        bad_urls = [u["url"] for u in c.get("urls", []) if u.get("status") != 200]
        if bad_urls:
            flags.append(f"url-fail x{len(bad_urls)}")
        print(f"  {p['qa_id']}  {c['chunk_tokens_est']:>5} tok  hard={c['topic_hard_total']:<3} {' '.join(flags)}")


if __name__ == "__main__":
    main()
