"""Lenh relabel (Phase B, spec 005 Session 2026-11-08): LLM cham lai topic, do kho, interview_style cho cap crawl.

Chi doc du lieu (khong sua data/raw/enriched_qa/); ket qua cache theo model o
data/raw/relabel/judgments-<model>.jsonl de so nhieu model tren cung cap va chay tiep duoc (bo qua cap da cham cung
prompt_version va cung topic). Cham moi cap qua luat muc cap, TRUOC dedup: bo mot cap thi cap trung cau hoi voi no
(truoc thua dedup) se thanh hop le, nen cung phai co nhan. Loi API va dau ra hong khong cache, lan sau thu lai.
Can RELABEL_API_KEY hoac EMBEDDING_API_KEY, khong can DB.
"""
import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from openai import OpenAI

from .qa_relabel_prompt import PROMPT_VERSION, build_messages, parse_judgment, topics_block
from .qa_seed_loader import SeedError, load_seed_items
from .qa_seed_rules import check_pair
from .settings import (CRAWLED_DATASET, ENRICHED_DIR, RELABEL_DIR, ConfigError, RelabelSettings, catalog_dir,
                       require_relabel_settings)
from .topic_catalog_reader import CatalogError, load_topics

BATCH_SIZE = 50
# (noi dung, prompt tokens, completion tokens, chi phi USD neu provider tra ve)
Judged = Tuple[str, int, int, Optional[float]]
JudgeFn = Callable[[List[Dict[str, str]]], Judged]


def request_params(s: RelabelSettings) -> Dict:
    """Tham so theo provider; reasoning va gioi han token lay tu env de so model voi cung cau hinh.
    OpenAI (model reasoning): reasoning_effort + max_completion_tokens, khong nhan temperature khac mac dinh.
    OpenRouter: reasoning trong extra_body, usage.cost la chi phi that."""
    if s.openrouter:
        extra: Dict = {"usage": {"include": True}}
        if s.reasoning:
            extra["reasoning"] = {"effort": s.reasoning}  # OpenRouter: effort "none" tat reasoning
        return {"temperature": 0, "max_tokens": s.max_tokens, "extra_body": extra}
    params: Dict = {"max_completion_tokens": s.max_tokens}
    if s.reasoning:
        params["reasoning_effort"] = s.reasoning
    return params


class JudgeClient:
    """Cung prompt, khong response_format (Claude va OpenAI nhan cung noi dung)."""

    def __init__(self, settings: RelabelSettings):
        self._client = OpenAI(base_url=settings.base_url, api_key=settings.api_key, max_retries=3, timeout=120)
        self._settings, self._params = settings, request_params(settings)

    def complete(self, messages: List[Dict[str, str]]) -> Judged:
        response = self._client.chat.completions.create(model=self._settings.model, messages=messages, **self._params)
        choice = response.choices[0]
        if not choice.message.content:  # vd reasoning dung het max_tokens: bao loi (khong cache) thay vi bad_json
            raise RuntimeError(f"tra loi rong, finish_reason={choice.finish_reason}")
        usage = response.usage
        cost = (getattr(usage, "model_extra", None) or {}).get("cost") if usage else None
        return (choice.message.content, usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0, cost)


def cache_path(model: str, out_dir: Path = RELABEL_DIR) -> Path:
    return out_dir / f"judgments-{re.sub(r'[^a-z0-9.-]+', '_', model.lower())}.jsonl"


def read_cache(path: Path) -> Dict[str, Dict]:
    """Dong sau ghi de dong truoc cung qa_id; dong hong (vd bi cat khi dung giua chung) bi bo qua."""
    if not path.exists():
        return {}
    rows: Dict[str, Dict] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            row = json.loads(line) if line.strip() else None
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("qa_id"):
            rows[row["qa_id"]] = row
    return rows


def is_current(row: Optional[Dict], pair: Dict) -> bool:
    """Nhan cache con dung: cung prompt_version va cham tren dung topic dang gan (enrich lai co the doi topic)."""
    return bool(row) and row.get("prompt_version") == PROMPT_VERSION and row.get("topic_before") == pair["topic_id"]


def read_ids(path: Path) -> List[str]:
    """Danh sach qa_id: mang JSON hoac moi dong mot id (chap nhan BOM cua Notepad / PowerShell)."""
    text = path.read_text(encoding="utf-8-sig")
    ids = json.loads(text) if text.lstrip().startswith("[") else text.split()
    return [str(i).strip() for i in ids if str(i).strip()]


def crawled_pairs(extra_catalog: Sequence[str], enriched_dir: Path = ENRICHED_DIR) -> Tuple[List[Dict], List[Dict]]:
    """Cap crawl qua luat muc cap (schema, topic, do dai, PII), TRUOC dedup, voi nhan goc luc enrich (khong ap
    decisions.json), va catalog topic."""
    topics = load_topics([catalog_dir()] + [Path(d) for d in extra_catalog])
    categories = {t["id"]: t["category"] for t in topics}
    items = load_seed_items([(enriched_dir, CRAWLED_DATASET)])
    return [item.data for item in items if not check_pair(item, categories)], topics


def judge_pairs(pairs: Sequence[Dict], topics: Sequence[Dict], judge: JudgeFn, out_path: Path, model: str,
                workers: int = 8) -> Counter:
    """Cham cac cap chua co nhan con dung trong cache, ghi them vao cache sau moi lo. Tra bo dem (ca token, chi phi)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    titles = {t["id"]: t["title"] for t in topics}
    topic_ids, topics_text = set(titles), topics_block(topics)
    done = read_cache(out_path)
    todo = [p for p in pairs if not is_current(done.get(p["qa_id"]), p)]
    stats: Counter = Counter(cached=len(pairs) - len(todo))
    failures = 0

    def work(pair: Dict):
        try:
            text, p_tok, c_tok, cost = judge(build_messages(pair, topics_text, titles.get(pair["topic_id"], "")))
        except Exception as exc:  # loi mang / provider sau retry: dem, khong cache
            return pair, None, f"error: {type(exc).__name__}: {str(exc)[:200]}", (0, 0, None)
        judgment, reason = parse_judgment(text, pair["topic_id"], topic_ids)
        return pair, judgment, reason, (p_tok, c_tok, cost)

    for start in range(0, len(todo), BATCH_SIZE):
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(work, todo[start : start + BATCH_SIZE]))
        rows = []
        for pair, judgment, reason, (p_tok, c_tok, cost) in results:
            stats["tokens_in"] += p_tok
            stats["tokens_out"] += c_tok
            stats["cost_micro_usd"] += round((cost or 0) * 1e6)
            if judgment is None:
                stats["error" if reason.startswith("error") else f"invalid:{reason}"] += 1
                failures += 1
                if failures <= 3:  # vai mau de chan doan, khong in het
                    print(f"[loi] {pair['qa_id']}: {reason}", file=sys.stderr)
                continue
            stats["judged"] += 1
            rows.append({"qa_id": pair["qa_id"], "model": model, "prompt_version": PROMPT_VERSION,
                         "topic_before": pair["topic_id"], "difficulty_before": pair["difficulty"], **judgment,
                         "tokens_in": p_tok, "tokens_out": c_tok, "cost": cost})
        with out_path.open("a", encoding="utf-8") as handle:
            handle.writelines(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        print(f"{start + len(results):>5}/{len(todo)} xong")
    return stats


def run_relabel(args: argparse.Namespace) -> int:
    try:
        settings = require_relabel_settings(args.model or "")
        pairs, topics = crawled_pairs(args.extra_catalog)
        ids = read_ids(Path(args.ids)) if args.ids else None
    except (ConfigError, CatalogError, SeedError, OSError, ValueError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return 2
    if ids is not None:
        wanted = set(ids)
        pairs = [p for p in pairs if p["qa_id"] in wanted]
        missing = wanted - {p["qa_id"] for p in pairs}
        if missing:
            print(f"canh bao: {len(missing)} qa_id khong co trong cap crawl hop le, vd {sorted(missing)[:3]}", file=sys.stderr)
    if args.limit:
        pairs = pairs[: args.limit]
    out_path = cache_path(settings.model)
    stats = judge_pairs(pairs, topics, JudgeClient(settings).complete, out_path, settings.model, args.workers)
    cost = stats.pop("cost_micro_usd", 0) / 1e6  # khong con cap nao can cham thi bo dem khong co khoa nay
    cost_text = f"~{cost:.4f} USD" if cost else "provider khong bao (OpenAI: tinh tu token theo bang gia)"
    print(f"== relabel {settings.model} (reasoning={settings.reasoning or '-'}, max_tokens={settings.max_tokens}): "
          f"{dict(sorted(stats.items()))}; chi phi {cost_text} -> {out_path}")
    return 3 if stats["error"] else 0
