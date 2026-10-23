"""So sanh cach truy hoi cho truy van tieng Viet (rag-design muc 7.4): model embedding x cach dung truy van.

Cach dung truy van: raw | glossary (app/rag/query_expansion) | rewrite (LLM -> tieng Anh) | raw+rewrite.
Model: small tren ai_db dung chung (AI_DB_URL), large tren DB cuc bo da embed lai (evals/copy_corpus.py).
Khong ap bo loc category/difficulty cua golden set (run_rag co ap): so sanh cac cach tren cung dieu kien.
  python -m evals.retrieval_experiment --large-db postgresql://postgres:pg@localhost:5545/postgres
"""
import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List

from app.llm.gateway import build_client, get_gateway
from app.llm.settings import load_llm_settings
from app.llm.usage import UsageCollector
from app.rag.models import SearchFilters
from app.rag.query_expansion import expand_query
from app.rag.query_rewrite import QueryRewriter
from app.rag.repository import PgKnowledgeRepository
from app.rag.retriever import OVERFETCH, dedup
from app.rag.settings import RagSettings, load_rag_settings
from evals.rag_metrics import recall_by_group

EVALS = Path(__file__).parent
SETS = {"main": EVALS / "rag_golden.json", "holdout": EVALS / "rag_golden_holdout.json"}
STRATEGIES = ("raw", "glossary", "rewrite", "raw+rewrite")


def texts_for(query: str, rewritten: str) -> Dict[str, str]:
    # raw+rewrite giong Retriever.search_text: viet lai loi (tra truy van goc) thi dung tu dien
    combined = f"{query}\n{rewritten}" if rewritten.strip() != query.strip() else expand_query(query)
    return {"raw": query, "glossary": expand_query(query), "rewrite": rewritten, "raw+rewrite": combined}


async def run(large_db: str, k: int = 5) -> Dict:
    shared = load_rag_settings()
    repos = {"small": PgKnowledgeRepository(shared)}
    if large_db:
        repos["large"] = PgKnowledgeRepository(RagSettings(True, large_db, "text-embedding-3-large", 10))
    client, rewriter, col = build_client(load_llm_settings()), QueryRewriter(get_gateway()), UsageCollector()
    rewrite_ms: List[float] = []
    results: Dict[str, Dict[str, List[dict]]] = {}
    for set_name, path in SETS.items():
        golden = json.loads(path.read_text(encoding="utf-8"))
        for q in golden["queries"]:
            t0 = time.perf_counter()
            rewritten = await rewriter.to_english(q["query"], col)
            rewrite_ms.append((time.perf_counter() - t0) * 1000)
            variants = texts_for(q["query"], rewritten)
            for model, repo in repos.items():
                name = f"openai/text-embedding-3-{model}"
                resp = await client.embeddings.create(model=name, input=list(variants.values()), dimensions=1536)
                for (strategy, _), emb in zip(variants.items(), resp.data):
                    hits = dedup(await repo.search(emb.embedding, SearchFilters(("interview_qa",)), k * OVERFETCH))[:k]
                    results.setdefault(set_name, {}).setdefault(f"{model}/{strategy}", []).append(
                        {"group": q["group"], "relevant": q["relevant"], "retrieved": [c.dedup_key for c in hits],
                         "id": q["id"], "rewritten": rewritten})
    table = {s: {cfg: recall_by_group(rows, k) for cfg, rows in cfgs.items()} for s, cfgs in results.items()}
    rewrite_ms.sort()
    return {"recall": table, "rewrite_ms_p50": round(rewrite_ms[len(rewrite_ms) // 2]),
            "rewrite_ms_p95": round(rewrite_ms[int(len(rewrite_ms) * 0.95) - 1]),
            "rewrite_usage": col.to_metadata()["usage"], "rows": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--large-db", default="")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = asyncio.run(run(args.large_db))
    for set_name, cfgs in report["recall"].items():
        for cfg, stats in cfgs.items():
            groups = " ".join(f"{g}={v['recall']:.3f}" for g, v in sorted(stats.items()))
            print(f"{set_name:8s} {cfg:20s} {groups}")
    print("rewrite latency ms p50/p95", report["rewrite_ms_p50"], report["rewrite_ms_p95"], report["rewrite_usage"])
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
