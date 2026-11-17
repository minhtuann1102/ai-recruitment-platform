import pytest

from pipeline.knowledge_chunk_search import build_search_sql, dedup_by_qa_id
from pipeline.knowledge_chunk_writer import plan_writes, vector_literal
from pipeline.knowledge_chunk_writer import write_records


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


# --- spec 012 (research R8): source_type theo ban ghi, don ban ghi dung source_type cua dataset ---


def typed_record(content_hash, dataset, source_type):
    return {  # du cot de nhanh UPDATE cua write_records chay duoc tren cursor gia
        "content": f"noi dung {content_hash}", "content_hash": content_hash, "source_type": source_type,
        "category": "Backend", "difficulty": None, "topic_id": None, "language": "en", "metadata": {"dataset": dataset},
    }


class FakeCursor:
    """Ghi lai cac lenh SQL; chi can cho nhanh don cua write_records (khong co ban ghi moi / update)."""

    def __init__(self):
        self.calls = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()

    def cursor(self):
        return self.cur

    def commit(self):
        pass


def test_source_types_follow_the_record_of_each_dataset_in_a_mixed_run():
    plan = plan_writes(
        [typed_record("a", "de_interview_qa", "interview_qa"), typed_record("t", "de_textbook_postgresql", "textbook")], {}
    )
    assert plan.source_types == {"de_interview_qa": "interview_qa", "de_textbook_postgresql": "textbook"}
    assert plan.keep_hashes == {"de_interview_qa": ["a"], "de_textbook_postgresql": ["t"]}


def test_record_without_source_type_is_interview_qa_as_before():
    assert plan_writes([record("a")], {}).source_types == {"de_interview_qa": "interview_qa"}


def test_textbook_hash_in_other_dataset_is_skipped_and_same_dataset_is_updated():
    records = [typed_record("other", "de_textbook_postgresql", "textbook"), typed_record("same", "de_textbook_postgresql", "textbook")]
    plan = plan_writes(records, {"other": "de_textbook_spring-boot", "same": "de_textbook_postgresql"})
    assert [r["content_hash"] for r in plan.skip_other] == ["other"]
    assert [r["content_hash"] for r in plan.update] == ["same"]
    assert plan.new == []


def test_one_dataset_with_two_source_types_is_rejected():
    with pytest.raises(ValueError, match="hai source_type"):
        plan_writes([typed_record("a", "de_x", "interview_qa"), typed_record("b", "de_x", "textbook")], {})


def test_cleanup_deletes_with_source_type_of_each_dataset():
    plan = plan_writes(
        [typed_record("a", "de_interview_qa", "interview_qa"), typed_record("t", "de_textbook_postgresql", "textbook")], {"a": "de_interview_qa", "t": "de_textbook_postgresql"}
    )
    conn = FakeConn()
    stats = write_records(conn, plan, embed=lambda texts: [], stored_model="m")
    deletes = [params for sql, params in conn.cur.calls if sql.lstrip().startswith("DELETE")]
    assert deletes == [("interview_qa", "de_interview_qa", ["a"]), ("textbook", "de_textbook_postgresql", ["t"])]
    assert stats["cleanup"] == "done"
