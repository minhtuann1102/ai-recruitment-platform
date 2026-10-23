"""Do recall@5 cua duong doc RAG tren golden set (rag-design muc 7, NFR-AI-QUAL14).

Can: ai_db co du lieu DE (RAG_ENABLED=true, AI_DB_URL) va LLM_API_KEY de embed truy van (ton vai cent).
Chay: cd apps/ai-service && python -m evals.run_rag [--golden evals/rag_golden.json] [--out report.json]
Do vector search thuan (khong qua tra theo topic_id) vi golden set kiem chat luong embedding.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.llm.gateway import get_gateway
from app.rag.models import SearchFilters
from app.rag.factory import build_retriever
from app.rag.repository import PgKnowledgeRepository
from app.rag.retriever import OVERFETCH, dedup
from app.rag.settings import load_rag_settings
from evals.rag_metrics import hit_at_k, recall_by_group

DEFAULT_GOLDEN = Path(__file__).with_name("rag_golden.json")


async def evaluate(golden: dict, expand: bool = True) -> dict:
    """expand=True: dung dung van ban tim kiem nhu retriever (LLM viet lai neu RAG_QUERY_REWRITE bat, khong thi
    tu dien); expand=False: truy van goc."""
    settings = load_rag_settings()
    if not settings.enabled:
        raise SystemExit("Dat RAG_ENABLED=true va AI_DB_URL truoc khi chay eval")
    repo, gateway, k = PgKnowledgeRepository(settings), get_gateway(), golden.get("k", 5)
    retriever = build_retriever(settings, gateway)
    results = []
    for q in golden["queries"]:
        text = await retriever.search_text(q["query"]) if expand else q["query"]
        vector = (await gateway.embed([text]))[0]
        f = q.get("filters", {})
        filters = SearchFilters(("interview_qa",), f.get("category"), f.get("difficulty"), None)
        hits = dedup(await repo.search(vector, filters, k * OVERFETCH))[:k]
        retrieved = [c.dedup_key for c in hits]
        results.append({"id": q["id"], "group": q["group"], "relevant": q["relevant"], "retrieved": retrieved,
                        "scores": [round(c.score or 0.0, 3) for c in hits]})
        mark = "OK  " if hit_at_k(retrieved, q["relevant"], k) else "MISS"
        print(f"{mark} {q['id']} [{q['group']}] top={retrieved[:3]}", file=sys.stderr)
    return {"k": k, "embedding_model": settings.embedding_model, "query_expansion": expand, "query_rewrite": settings.query_rewrite, "recall": recall_by_group(results, k),
            "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--no-expand", action="store_true", help="tat mo rong truy van (de so sanh)")
    args = parser.parse_args()
    report = asyncio.run(evaluate(json.loads(args.golden.read_text(encoding="utf-8")), expand=not args.no_expand))
    for group, stat in sorted(report["recall"].items()):
        print(f"{group:15s} n={stat['n']:3d} recall@{report['k']}={stat['recall']:.3f}")
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
