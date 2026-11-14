"""Do Evaluator tu tra cuu (phase 03) tren golden set: --lookup cua run_evaluator / run_evaluator_sourced.

Golden dung `EvaluationInput` khong qua turn_evaluation nen khong tu co `lookup`: neu khong dung o day thi co bat hay tat
cung cho cung ket qua (audit H3). Day la XAP XI cua production: mau golden khong co `catalog_ref` nen category = None
(rong hon production, nhat la track java_backend: moi category trong kho); BM25 nap tu ai_db (can AI_DB_URL, RAG_ENABLED).
"""
from typing import Dict, List, Optional

from app.agents.evaluator import EvaluationInput
from app.evaluator_lookup import TurnLookup, build_lookup, load_lookup_settings
from app.plan_snippets import memory_retriever


async def load_lookup_retriever():
    """Retriever co BM25 da nap (bo nho). SystemExit khi RAG tat / khong co hybrid: khong chay --lookup gia."""
    retriever = memory_retriever()
    if retriever is None or getattr(retriever, "hybrid", None) is None:
        raise SystemExit("--lookup can RAG_ENABLED=true, RAG_HYBRID=true va AI_DB_URL de nap corpus BM25")
    await retriever.hybrid.bm25.index()  # nap truoc: tim co han se coi corpus chua nap la khong co ket qua
    if not retriever.turn_retrieval:
        raise SystemExit("--lookup can RAG_TURN_RETRIEVAL=true (cung dieu kien voi production)")
    return retriever


def attach_lookup(retriever, sample: dict, inp: EvaluationInput) -> Optional[TurnLookup]:
    """Gan TurnLookup moi cho mot lan chay (trang thai theo lan chay); None neu mau co R / intro / khong co pham vi."""
    if retriever is None or inp.reference_answer:
        return None
    inp.lookup = build_lookup(retriever, sample.get("track", "java_backend"), phase=inp.phase, topic=inp.topic,
                              difficulty=inp.difficulty, turn_snippets_=inp.turn_snippets,
                              settings=load_lookup_settings({"EVALUATOR_TOOLS": "true"}))
    return inp.lookup


def lookup_fields(lookup: Optional[TurnLookup]) -> Dict:
    """Truong them vao ket qua mot lan chay: chi khi luot co lookup."""
    if lookup is None:
        return {}
    return {"lookup": True, "tool_queries": len(lookup.queries), "tool_chunks": len(lookup.texts),
            "lookup_committed": lookup.committed}


def lookup_summary(runs: List[dict]) -> Dict:
    """Tong ket tren cac lan chay co lookup: ty le goi cong cu, ty le tim rong, vong lap loi (khong committed)."""
    looked = [r for r in runs if r.get("lookup")]
    if not looked:
        return {"eligible_runs": 0}
    called = [r for r in looked if r["tool_queries"]]
    return {"eligible_runs": len(looked), "lookup_rate": round(len(called) / len(looked), 3),
            "empty_rate": round(sum(r["tool_chunks"] == 0 for r in called) / len(called), 3) if called else None,
            "loop_failed": sum(not r["lookup_committed"] for r in looked)}
