"""Lenh enrich: data/raw/collected_qa/*.jsonl -> data/raw/enriched_qa/<nguon>.json (dinh dang seed).

Chay tiep duoc: bo qua cid da co trong file ket qua hoac _rejected.jsonl; ghi sau moi lo 100 cap.
Loi goi API (sau retry) khong luu cache nen lan sau thu lai. Can LLM_API_KEY, khong can DB.
"""
import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Set

from .collect_command import COLLECTED_DIR
from .llm_enricher import CompleteFn, LlmClient, build_messages, parse_response, to_seed_pair, topics_block
from .settings import ENRICHED_DIR, ConfigError, catalog_dir, require_llm_settings
from .topic_catalog_reader import CatalogError, load_topics

BATCH_SIZE = 100
REJECTED_FILE = "_rejected.jsonl"
# Gia gpt-4o-mini (USD / 1M token) chi de uoc tinh chi phi in ra
PRICE_IN, PRICE_OUT = 0.15, 0.60


def _read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _done_ids(out_dir: Path, retry_rejected: bool) -> Set[str]:
    done = {pair["qa_id"] for f in out_dir.glob("*.json") for pair in json.loads(f.read_text(encoding="utf-8"))}
    if not retry_rejected:
        done |= {row["cid"] for row in _read_jsonl(out_dir / REJECTED_FILE)}
    return done


def _write_source(out_dir: Path, source: str, new_pairs: List[Dict]) -> None:
    path = out_dir / f"{source}.json"
    pairs = {p["qa_id"]: p for p in (json.loads(path.read_text(encoding="utf-8")) if path.exists() else [])}
    pairs.update({p["qa_id"]: p for p in new_pairs})
    path.write_text(json.dumps(sorted(pairs.values(), key=lambda p: p["qa_id"]), ensure_ascii=False, indent=1), encoding="utf-8")


def enrich_all(args: argparse.Namespace, topics: List[Dict], complete: CompleteFn,
               collected_dir: Path = COLLECTED_DIR, out_dir: Path = ENRICHED_DIR) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    topics_text, topic_ids = topics_block(topics), {t["id"] for t in topics}
    done = _done_ids(out_dir, args.retry_rejected)
    stats, tokens = Counter(), Counter()

    def work(record: Dict):
        try:
            text, prompt_tokens, completion_tokens = complete(build_messages(record, topics_text))
        except Exception as exc:  # loi mang / provider sau retry: dem, khong cache
            return record, None, f"error: {type(exc).__name__}", (0, 0)
        enriched, reason = parse_response(text, record, topic_ids)
        return record, enriched, reason, (prompt_tokens, completion_tokens)

    for path in sorted(collected_dir.glob("*.jsonl")):
        source = path.stem
        if args.only and source not in args.only:
            continue
        todo = [r for r in _read_jsonl(path) if r["cid"] not in done]
        if args.per_source:
            todo = todo[: args.per_source]
        for start in range(0, len(todo), BATCH_SIZE):
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                results = list(pool.map(work, todo[start : start + BATCH_SIZE]))
            pairs, rejected = [], []
            for record, enriched, reason, (p_tok, c_tok) in results:
                tokens["in"] += p_tok
                tokens["out"] += c_tok
                if enriched:
                    pairs.append(to_seed_pair(record, enriched))
                    stats["enriched"] += 1
                elif reason.startswith("error"):
                    stats["errors"] += 1
                else:
                    rejected.append({"cid": record["cid"], "source": source, "reason": reason})
                    stats[f"rejected:{reason}"] += 1
            _write_source(out_dir, source, pairs)
            with (out_dir / REJECTED_FILE).open("a", encoding="utf-8") as handle:
                handle.writelines(json.dumps(row, ensure_ascii=False) + "\n" for row in rejected)
            print(f"{source:<28} {start + len(results):>5}/{len(todo)} xong")

    cost = tokens["in"] / 1e6 * PRICE_IN + tokens["out"] / 1e6 * PRICE_OUT
    print(f"== enrich: {dict(sorted(stats.items()))}; token in/out {tokens['in']}/{tokens['out']} (~{cost:.2f} USD gpt-4o-mini)")
    return 3 if stats["errors"] else 0


def run_enrich(args: argparse.Namespace) -> int:
    try:
        settings = require_llm_settings()
        topics = load_topics([catalog_dir()] + [Path(d) for d in args.extra_catalog])
    except (ConfigError, CatalogError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return 2
    return enrich_all(args, topics, LlmClient(settings).complete)
