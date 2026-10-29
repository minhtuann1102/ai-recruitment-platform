"""Retriever (FR-AI-022, 061): topic_id truoc, vector fallback, khu trung, ngan sach token, chiu loi."""
import asyncio
import logging

import pytest

from app.rag.retriever import Retriever, build_query, dedup, estimate_tokens, trim_to_budget
from tests.fakes.fake_knowledge_repo import FakeEmbed, FakeKnowledgeRepo, qa, textbook

TOPIC = "node.core.event-loop"


def run(coro):
    return asyncio.run(coro)


def retrieve(retriever, **kw):
    args = {"topic_id": TOPIC, "category": "Backend", "difficulty": 3, "query": "Backend | Event loop"}
    return run(retriever.retrieve_for_topic(**{**args, **kw}))


def test_enough_topic_hits_skips_vector_search():
    repo, embed = FakeKnowledgeRepo(by_topic=[qa("q1", TOPIC), qa("q2", TOPIC)]), FakeEmbed()
    out = retrieve(Retriever(repo, embed))
    assert [c.qa_id for c in out] == ["q1", "q2"]
    assert embed.queries == [] and [c[0] for c in repo.calls] == ["topic"]
    assert repo.calls[0][2] == "medium"  # do kho 3 -> medium


def test_fewer_than_two_topic_hits_falls_back_to_vector_and_dedups():
    repo = FakeKnowledgeRepo(by_topic=[qa("q1", TOPIC)],
                             hits=[qa("q1", TOPIC, chunk_type="question", score=0.9),
                                   qa("q7", "node.other", score=0.8), textbook("t1", score=0.7)])
    embed = FakeEmbed()
    out = retrieve(Retriever(repo, embed, textbook=True))
    assert [c.dedup_key for c in out] == ["q1", "q7", "t1"]
    assert out[0].chunk_type == "qa_pair"  # ban topic_id (qa_pair) giu truoc ban question trung qa_id
    _, filters, limit = repo.calls[1]
    assert filters.source_types == ("interview_qa", "textbook")
    assert (filters.category, filters.difficulty, filters.chunk_type) == ("Backend", "medium", "qa_pair")
    assert limit == 20 and embed.queries == ["Backend | Event loop"]


def test_scenario_mode_uses_textbook_only():
    repo = FakeKnowledgeRepo(hits=[qa("q9", TOPIC, score=0.9), textbook("t1")])
    out = retrieve(Retriever(repo, FakeEmbed(), textbook=True), topic_id=None, include_qa=False)
    assert [c.id for c in out] == ["t1"]
    assert [c[0] for c in repo.calls] == ["search"]
    assert repo.calls[0][1].source_types == ("textbook",)


def test_top_k_and_token_budget():
    chunks = [qa(f"q{i}", TOPIC, content="x" * 300) for i in range(8)]  # 100 token moi chunk
    out = retrieve(Retriever(FakeKnowledgeRepo(by_topic=chunks), FakeEmbed()), token_budget=250)
    assert len(out) == 3 and out[-1].content.endswith(" ...")
    assert sum(estimate_tokens(c.content) for c in out) <= 250
    assert len(retrieve(Retriever(FakeKnowledgeRepo(by_topic=chunks), FakeEmbed()))) == 5


def test_plan_snippets_max_three_and_600_tokens():
    chunks = [qa(f"q{i}", TOPIC, content="y" * 900) for i in range(5)]  # 300 token moi chunk
    snippets = run(Retriever(FakeKnowledgeRepo(by_topic=chunks), FakeEmbed()).plan_snippets(
        topic_id=TOPIC, category="Backend", difficulty=2, query="q"))
    assert 1 <= len(snippets) <= 3
    assert sum(estimate_tokens(s.content) for s in snippets) <= 600


@pytest.mark.parametrize("repo,embed", [
    (FakeKnowledgeRepo(fail=OSError("db down")), FakeEmbed()),
    (FakeKnowledgeRepo(), FakeEmbed(fail=RuntimeError("embedding loi"))),
])
def test_failures_return_empty_instead_of_raising(repo, embed, caplog):
    with caplog.at_level(logging.WARNING, logger="ai_service.rag"):
        assert retrieve(Retriever(repo, embed)) == []
    assert "rag_retrieve_failed" in caplog.text


def test_bad_difficulty_does_not_raise_and_question_mode_filter():
    assert retrieve(Retriever(FakeKnowledgeRepo(), FakeEmbed()), difficulty=9) == []
    repo = FakeKnowledgeRepo(hits=[qa("q3", TOPIC, chunk_type="question", score=0.7)])
    out = retrieve(Retriever(repo, FakeEmbed()), chunk_type="question")
    assert [c.qa_id for c in out] == ["q3"] and repo.calls[-1][1].chunk_type == "question"


def test_logs_ids_and_scores_not_content(caplog):
    repo = FakeKnowledgeRepo(hits=[qa("q5", TOPIC, content="BI MAT NOI DUNG", score=0.812)])
    with caplog.at_level(logging.INFO, logger="ai_service.rag"):
        retrieve(Retriever(repo, FakeEmbed()))
    assert "q5:0.812" in caplog.text and "BI MAT" not in caplog.text


def test_reference_answer_by_qa_id_and_failure():
    repo = FakeKnowledgeRepo(by_topic=[qa("q1", TOPIC), qa("q1", TOPIC, chunk_type="question")])
    found = run(Retriever(repo, FakeEmbed()).reference_answer("q1"))
    assert found.chunk_type == "qa_pair" and repo.calls == [("pair", "q1")]
    assert run(Retriever(FakeKnowledgeRepo(fail=OSError()), FakeEmbed()).reference_answer("q1")) is None


def test_helpers():
    assert [c.qa_id for c in dedup([qa("a", TOPIC), qa("a", TOPIC, chunk_type="question"), qa("b", TOPIC)])] \
        == ["a", "b"]
    assert trim_to_budget([qa("a", TOPIC, content="z" * 30)], 5) == []
    assert build_query("Backend", "Event loop", "  tra loi " + "w" * 500).startswith("Backend | Event loop | tra loi")
    assert len(build_query(None, "T", "w" * 500)) == len("T | ") + 300


def test_textbook_disabled_skips_scenario_and_textbook_search():
    repo, embed = FakeKnowledgeRepo(hits=[textbook("t1")]), FakeEmbed()
    assert retrieve(Retriever(repo, embed), topic_id=None, include_qa=False) == []
    assert repo.calls == [] and embed.queries == []  # khong ton DB hay embed
    retrieve(Retriever(repo, embed))
    assert repo.calls[-1][1].source_types == ("interview_qa",)


def test_vector_query_is_expanded_with_english_terms():
    embed = FakeEmbed()
    retrieve(Retriever(FakeKnowledgeRepo(), embed), query="Phân trang làm trang cuối rất chậm")
    assert embed.queries == ["Phân trang làm trang cuối rất chậm (pagination offset limit)"]
