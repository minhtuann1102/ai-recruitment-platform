from pipeline.knowledge_chunk_search import build_search_sql, dedup_by_qa_id
from pipeline.knowledge_chunk_writer import plan_writes, vector_literal


def record(content_hash, qa_id="de-qa-0001", chunk_type="qa_pair", dataset="de_interview_qa"):
    return {"content_hash": content_hash, "metadata": {"qa_id": qa_id, "chunk_type": chunk_type, "dataset": dataset}}


def test_rerun_with_everything_indexed_has_no_new_records():
    records = [record("a"), record("b", chunk_type="question")]
    plan = plan_writes(records, {"a": "de_interview_qa", "b": "de_interview_qa"})
    assert plan.new == [] and len(plan.update) == 2
    assert plan.keep_hashes == {"de_interview_qa": ["a", "b"]}


def test_edited_answer_is_new_and_old_hash_is_not_kept():
    # dap an sua -> hash qa_pair moi "a2"; hash cu "a1" khong con trong keep -> bi DELETE o buoc don
    plan = plan_writes([record("a2"), record("q", chunk_type="question")], {"a1": "de_interview_qa", "q": "de_interview_qa"})
    assert [r["content_hash"] for r in plan.new] == ["a2"]
    assert "a1" not in plan.keep_hashes["de_interview_qa"]


def test_hash_owned_by_other_dataset_is_skipped_not_updated():
    plan = plan_writes([record("x", dataset="de_crawled_qa")], {"x": "ai_mock_seed"})
    assert plan.new == [] and plan.update == [] and len(plan.skip_other) == 1


def test_keep_hashes_are_grouped_per_dataset():
    plan = plan_writes([record("a"), record("b", dataset="de_crawled_qa")], {})
    assert plan.keep_hashes == {"de_interview_qa": ["a"], "de_crawled_qa": ["b"]}


def test_dedup_by_qa_id_keeps_best_row_per_pair_then_cuts_k():
    rows = [
        {"qa_id": "q1", "score": 0.9},
        {"qa_id": "q1", "score": 0.8},
        {"qa_id": "q2", "score": 0.7},
        {"qa_id": "q3", "score": 0.6},
    ]
    assert [r["qa_id"] for r in dedup_by_qa_id(rows, 2)] == ["q1", "q2"]


def test_search_sql_always_filters_model_and_applies_optional_filters():
    sql, params = build_search_sql({"category": "Backend", "chunk_type": "qa_pair", "difficulty": None}, "text-embedding-3-small", [0.5, 1.0], 20)
    assert "embedding_model = %s" in sql and "category = %s" in sql and "metadata->>'chunk_type' = %s" in sql
    assert "difficulty = %s" not in sql
    assert params == ["[0.5,1.0]", "interview_qa", "text-embedding-3-small", "Backend", "qa_pair", "[0.5,1.0]", 20]


def test_vector_literal_format():
    assert vector_literal([1, 0.25]) == "[1.0,0.25]"
