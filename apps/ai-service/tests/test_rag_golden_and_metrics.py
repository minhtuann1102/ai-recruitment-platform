"""Golden set RAG dung dinh dang (rag-design muc 9) va ham recall@k dung."""
import json
from collections import Counter
from pathlib import Path

from evals.rag_metrics import hit_at_k, recall_by_group

GOLDEN = json.loads((Path(__file__).resolve().parent.parent / "evals" / "rag_golden.json").read_text("utf-8"))


def test_golden_set_shape():
    queries = GOLDEN["queries"]
    assert len(queries) >= 20 and GOLDEN["k"] == 5
    assert len({q["id"] for q in queries}) == len(queries)
    assert len({q["query"] for q in queries}) == len(queries)
    for q in queries:
        assert q["group"] in GOLDEN["groups"]
        assert q["relevant"] and all(r.startswith("de-qa-") for r in q["relevant"])
    counts = Counter(q["group"] for q in queries)
    assert all(counts[g] >= 4 for g in ("vi", "mixed", "en", "no_diacritics"))


def test_hit_and_recall_by_group():
    assert hit_at_k(["a", "b", "c"], ["c"], 3) and not hit_at_k(["a", "b", "c"], ["c"], 2)
    stats = recall_by_group([
        {"group": "vi", "retrieved": ["x", "y"], "relevant": ["y"]},
        {"group": "vi", "retrieved": ["x"], "relevant": ["z"]},
        {"group": "en", "retrieved": ["z"], "relevant": ["z", "w"]},
    ], 5)
    assert stats["vi"] == {"n": 2, "hits": 1, "recall": 0.5, "mrr": 0.25}  # y o hang 2 -> 1/2, chia 2 truy van
    assert stats["en"]["recall"] == 1.0 and stats["all"] == {"n": 3, "hits": 2, "recall": 0.667, "mrr": 0.5}
