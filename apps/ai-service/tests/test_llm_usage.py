from app.llm.usage import CallRecord, UsageCollector


def test_metadata_shape_matches_contract():
    c = UsageCollector()
    c.add(CallRecord("planner", "m", 100, 20, 900, "v1"))
    c.add(CallRecord("interviewer", "m", 50, 10, 300, "v2", fallback="backup_question"))
    c.add(CallRecord("planner", "m", 5, 5, 100))
    meta = c.to_metadata()
    assert meta["usage"] == {"planner": {"input_tokens": 105, "output_tokens": 25},
                             "interviewer": {"input_tokens": 50, "output_tokens": 10}}
    assert meta["latency_ms"] == {"planner": 1000, "interviewer": 300, "total": 1300}
    assert meta["prompt_versions"] == {"planner": "v1", "interviewer": "v2"}
    assert meta["fallbacks"] == ["backup_question"]
    assert c.total_tokens() == 190


def test_empty_collector():
    assert UsageCollector().to_metadata()["latency_ms"] == {"total": 0}
