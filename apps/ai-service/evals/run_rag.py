"""Do recall@5 cua duong doc RAG tren golden set (rag-design muc 7, NFR-AI-QUAL14).

Can: ai_db co du lieu DE (RAG_ENABLED=true, AI_DB_URL) va LLM_API_KEY de embed truy van (ton vai cent).
Chay: cd apps/ai-service && python -m evals.run_rag [--golden evals/rag_golden.json] [--mode vector|hybrid|both]
      [--out report.json]
vector: vector search thuan (kiem chat luong embedding). hybrid: tu khoa + vector gop RRF (app/rag/hybrid_search.py,
khong co danh sach topic_id vi golden set khong gan topic). both: chay ca hai tren cung truy van de so sanh.
Golden chinh co it truy van: doc cung held-out (--golden evals/rag_golden_holdout.json).
"""
import argparse
import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path

from app.llm.gateway import get_gateway
from app.rag.models import SearchFilters
from app.rag.factory import build_retriever
from app.rag.repository import PgKnowledgeRepository
from app.rag.retriever import OVERFETCH, dedup
from app.rag.settings import load_rag_settings
from evals.rag_metrics import hit_at_k, recall_by_group

DEFAULT_GOLDEN = Path(__file__).with_name("rag_golden.json")


async def evaluate(golden: dict, expand: bool = True, mode: str = "vector") -> dict:
    """expand=True: dung dung van ban tim kiem nhu retriever (LLM viet lai neu RAG_QUERY_REWRITE bat, khong thi
    tu dien); expand=False: truy van goc."""
    settings = load_rag_settings()
    if not settings.enabled:
        raise SystemExit("Dat RAG_ENABLED=true va AI_DB_URL truoc khi chay eval")
    repo, gateway, k = PgKnowledgeRepository(settings), get_gateway(), golden.get("k", 5)
    retriever = build_retriever(replace(settings, hybrid=True), gateway)
    results = []
    for q in golden["queries"]:
        f = q.get("filters", {})
        filters = SearchFilters(("interview_qa",), f.get("category"), f.get("difficulty"), None)
        if mode == "hybrid":
            hits = (await retriever.hybrid.search(q["query"], filters, k * OVERFETCH))[:k]
        else:
            text = await retriever.search_text(q["query"]) if expand else q["query"]
            vector = (await gateway.embed([text]))[0]
            hits = dedup(await repo.search(vector, filters, k * OVERFETCH))[:k]
        retrieved = [c.dedup_key for c in hits]
        results.append({"id": q["id"], "group": q["group"], "relevant": q["relevant"], "retrieved": retrieved,
                        "scores": [round(c.score or 0.0, 3) for c in hits]})
        mark = "OK  " if hit_at_k(retrieved, q["relevant"], k) else "MISS"
        print(f"{mark} {q['id']} [{q['group']}] top={retrieved[:3]}", file=sys.stderr)
    return {"k": k, "mode": mode, "embedding_model": settings.embedding_model, "query_expansion": expand,
            "query_rewrite": settings.query_rewrite, "recall": recall_by_group(results, k),
            "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--no-expand", action="store_true", help="tat mo rong truy van (de so sanh, chi mode vector)")
    parser.add_argument("--mode", choices=("vector", "hybrid", "both"), default="vector")
    args = parser.parse_args()
    golden = json.loads(args.golden.read_text(encoding="utf-8"))
    modes = ("vector", "hybrid") if args.mode == "both" else (args.mode,)
    reports = {m: asyncio.run(evaluate(golden, expand=not args.no_expand, mode=m)) for m in modes}
    for mode, report in reports.items():
        for group, stat in sorted(report["recall"].items()):
            print(f"{mode:7s} {group:15s} n={stat['n']:3d} recall@{report['k']}={stat['recall']:.3f} "
                  f"mrr={stat['mrr']:.3f}")
    if args.out:
        out = reports[modes[0]] if len(modes) == 1 else reports
        args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
