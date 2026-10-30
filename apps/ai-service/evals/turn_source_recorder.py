"""Ghi tai lieu Evaluator thay o moi luot (Phase 05 hybrid RAG).

Response chi co tai lieu duoc trich; muon biet vi sao mot y `no_source` thi phai co ca tai lieu khong duoc trich. Boc
`get_evaluator` cua turn_engine trong cung tien trinh, khong doi code service, nen khong co tac dung voi --base-url.
Text la dung chuoi trong prompt; ghi vao JSON bao cao (plans/reports/*.json, gitignored).
"""
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Tuple

import app.turn_engine as engine
from app.agents.evaluator import EvaluationInput, all_snippets, source_refs
from app.evaluator_source_checks import REFERENCE_ID, source_blocks
from app.llm.usage import UsageCollector
from app.logging_setup import bound_session_id, safe_session_id
from app.models_interview import Evaluation

Key = Tuple[Optional[str], int]  # (session_id, turn_number): topic id `t{n}` va cau hoi co the trung giua cac phien


def documents(inp: EvaluationInput) -> List[Dict]:
    """Tai lieu theo dung thu tu id S1.. / R; origin: topic (gan luc start), turn (truy hoi theo luot), reference."""
    topic = len(inp.topic.reference_snippets)
    out = []
    for n, ((block_id, text), ref) in enumerate(zip(source_blocks(all_snippets(inp), inp.reference_answer),
                                                    source_refs(inp))):
        origin = "reference" if block_id == REFERENCE_ID else "topic" if n < topic else "turn"
        out.append({"id": block_id, "origin": origin, "ref": ref.ref if ref else None, "text": text})
    return out


class _RecordingEvaluator:
    def __init__(self, inner, seen: Dict[Key, List[Dict]]):
        self.inner, self.seen = inner, seen

    async def evaluate(self, inp: EvaluationInput, collector: Optional[UsageCollector] = None) -> Evaluation:
        self.seen[(bound_session_id(), inp.turn_number)] = documents(inp)
        return await self.inner.evaluate(inp, collector)


@contextmanager
def record_documents() -> Iterator[Dict[Key, List[Dict]]]:
    seen: Dict[Key, List[Dict]] = {}
    real = engine.get_evaluator
    engine.get_evaluator = lambda: _RecordingEvaluator(real(), seen)
    try:
        yield seen
    finally:
        engine.get_evaluator = real


def attach_documents(sessions: Dict[str, Dict], seen: Dict[Key, List[Dict]]) -> None:
    """Gan `documents` vao tung luot; luot khong cham (wrap_up) hoac chay qua --base-url thi khong co khoa nay."""
    for pid, session in sessions.items():
        sid = safe_session_id(f"sim-{pid}")  # cung id run_session gui, bind_request da lam sach
        for t in session["turns"]:
            docs = seen.get((sid, t["turn_number"]))
            if docs is not None:
                t["documents"] = docs
