"""Phan thuan cua thi nghiem embedding (evals/embedding_experiment_*): cosine top-k + dedup, bootstrap CI, dem chunk bi cat,
cache vector, kiem tra id thieu. Vector gia, khong mang, khong can torch / sentence-transformers."""
import numpy as np
import pytest

from app.rag.models import Chunk
from evals import embedding_experiment_cache as cache
from evals.embedding_experiment_core import (count_truncated, normalize, paired_bootstrap_ci, per_query_metrics,
                                             percentile_ms, retrieve_keys, truncation_by_type, verdict)
from evals.embedding_experiment_corpus import parse_vector, precheck_missing
from evals.rag_metrics import hit_at_k, reciprocal_rank


def chunk(i: int, qa_id: str, chunk_type: str = "qa_pair") -> Chunk:
    return Chunk(id=f"id{i:03d}", content="", source_type="interview_qa", topic_id=None, category=None,
                 difficulty=None, qa_id=qa_id, chunk_type=chunk_type)


def test_normalize_unit_rows_and_zero_vector_kept():
    out = normalize(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert np.allclose(out[0], [0.6, 0.8]) and np.allclose(out[1], [0.0, 0.0]) and out.dtype == np.float32


def test_retrieve_keys_orders_by_cosine_and_dedups_by_qa_id():
    # 2 cap Q&A: moi cap co chunk question + qa_pair cung qa_id; chunk 4 (qa-c) xa truy van
    chunks = [chunk(0, "qa-a", "question"), chunk(1, "qa-a"), chunk(2, "qa-b", "question"), chunk(3, "qa-b"),
              chunk(4, "qa-c")]
    matrix = normalize(np.array([[1, 0.05], [1, 0.1], [0.9, 0.5], [0.8, 0.6], [0, 1]], dtype=np.float32))
    keys = retrieve_keys(matrix, chunks, normalize(np.array([1.0, 0.0])), k=5)
    assert keys == ["qa-a", "qa-b", "qa-c"]  # qa-a / qa-b chi tinh mot lan du co hai chunk


def test_retrieve_keys_overfetch_window_limits_k():
    # 12 qa_id, moi qa_id 2 chunk: top-k*OVERFETCH = 20 chunk -> du 10 qa_id, k=5 cat con 5
    chunks, vecs = [], []
    for i in range(12):
        for j, ct in enumerate(("question", "qa_pair")):
            chunks.append(chunk(2 * i + j, f"qa-{i:02d}", ct))
            vecs.append([1.0, 0.01 * i + 0.001 * j])
    keys = retrieve_keys(normalize(np.array(vecs, dtype=np.float32)), chunks, normalize(np.array([1.0, 0.0])), k=5)
    assert keys == [f"qa-{i:02d}" for i in range(5)]


def test_retrieve_keys_tie_break_is_stable_by_corpus_order():
    chunks = [chunk(0, "qa-x"), chunk(1, "qa-y"), chunk(2, "qa-z")]
    matrix = normalize(np.array([[1, 0], [1, 0], [1, 0]], dtype=np.float32))
    assert retrieve_keys(matrix, chunks, np.array([1.0, 0.0], dtype=np.float32), k=2) == ["qa-x", "qa-y"]


def test_per_query_metrics_match_rag_metrics():
    rows = [{"retrieved": ["a", "b", "c"], "relevant": ["c"]}, {"retrieved": ["a"], "relevant": ["z"]}]
    hits, rr = per_query_metrics(rows, 5)
    assert hits.tolist() == [1.0, 0.0] and np.allclose(rr, [1 / 3, 0.0])
    assert [bool(h) for h in hits] == [hit_at_k(r["retrieved"], r["relevant"], 5) for r in rows]
    assert list(rr) == [reciprocal_rank(r["retrieved"], r["relevant"], 5) for r in rows]


def test_bootstrap_all_zero_difference_is_tie():
    mean, lo, hi = paired_bootstrap_ci([0.0] * 24)
    assert (mean, lo, hi) == (0.0, 0.0, 0.0) and verdict(lo, hi) == "tie"  # [0, 0] khong tinh la thang


def test_bootstrap_consistent_gain_excludes_zero_and_loss_too():
    assert verdict(*paired_bootstrap_ci([1.0] * 20)[1:]) == "better"
    assert verdict(*paired_bootstrap_ci([-1.0] * 20)[1:]) == "worse"


def test_bootstrap_mixed_small_sample_is_tie_with_sane_bounds():
    diffs = [1, 1, -1, 0, 0, 1, 0, -1, 0, 1, 0, 0]  # +3 net tren 12 truy van: khong du de loai 0
    mean, lo, hi = paired_bootstrap_ci(diffs)
    assert lo < mean < hi and lo < 0 < hi and verdict(lo, hi) == "tie"


def test_bootstrap_is_deterministic_with_fixed_seed_and_seed_matters():
    d = list(np.random.default_rng(1).normal(0.1, 1.0, 40))
    assert paired_bootstrap_ci(d) == paired_bootstrap_ci(d)
    assert paired_bootstrap_ci(d, seed=1) != paired_bootstrap_ci(d, seed=2)
    assert paired_bootstrap_ci([]) is None


def test_verdict_boundaries_are_strict():
    assert verdict(0.0, 0.2) == "tie" and verdict(-0.2, 0.0) == "tie"
    assert verdict(0.01, 0.2) == "better" and verdict(-0.2, -0.01) == "worse"


def test_count_truncated_counts_only_strictly_longer_than_max_len():
    r = count_truncated([10, 128, 129, 500], 128)
    assert r == {"n": 4, "truncated": 2, "pct": 50.0, "max_len": 128}
    assert count_truncated([], 128)["pct"] == 0.0


def test_truncation_by_type_splits_pair_and_question():
    out = truncation_by_type([300, 20, 200, 10], ["qa_pair", "question", "qa_pair", "question"], 128)
    assert out["all"]["truncated"] == 2 and out["qa_pair"]["pct"] == 100.0 and out["question"]["truncated"] == 0


def test_percentile_ms_interpolates():
    assert percentile_ms([10, 20, 30, 40, 50], 50) == 30.0
    assert percentile_ms([0, 100], 95) == pytest.approx(95.0)


def test_vector_store_roundtrip_missing_and_config_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE", tmp_path / "c")
    cfg = {"model": "m", "revision": "r1", "doc_prefix": "", "dims": 2}
    store = cache.VectorStore("m-r1", cfg)
    assert store.missing(["h1", "h2"]) == ["h1", "h2"]
    store.add(["h1", "h2"], np.array([[1, 0], [0, 1]]))
    store.meta["note"] = "x"
    store.save()
    again = cache.VectorStore("m-r1", cfg)
    assert again.missing(["h1", "h2", "h3"]) == ["h3"] and again.meta == {"note": "x"}
    assert np.allclose(again.matrix(["h2", "h1"]), [[0, 1], [1, 0]])
    with pytest.raises(KeyError):
        again.matrix(["h3"])
    assert cache.VectorStore("m-r1", {**cfg, "revision": "r2"}).missing(["h1"]) == ["h1"]  # config doi -> bo cache cu
    assert (tmp_path / "c" / ".gitignore").read_text(encoding="utf-8").strip() == "*"  # noi dung crawl khong commit


def test_parse_vector_and_precheck_missing():
    assert parse_vector("[0.5,-1,2e-3]").tolist() == pytest.approx([0.5, -1.0, 0.002])
    versions = {"v": {"sets": {"main": {"queries": [
        {"id": "g1", "relevant": ["a"]}, {"id": "g2", "relevant": ["b", "x"]}, {"id": "g3", "relevant": ["y"]}]}}}}
    out = precheck_missing(versions, ["a", "b"])["v"]["main"]
    assert out["missing_ids"] == ["x", "y"] and out["n_relevant_ids"] == 4 and out["n_missing_ids"] == 2
    assert out["queries_all_relevant_missing"] == ["g3"] and out["queries_some_relevant_missing"] == ["g2"]
    assert out["recall_ceiling"] == pytest.approx(0.6667, abs=1e-4)
