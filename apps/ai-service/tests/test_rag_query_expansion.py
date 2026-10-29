"""Mo rong truy van tieng Viet (rag-design muc 7.4) va ghi usage embedding cua RAG vao metadata (FR-AI-080)."""
import asyncio

from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from app.llm.usage import UsageCollector
from app.rag.factory import build_retriever
from app.rag.query_expansion import english_terms, expand_query
from app.rag.settings import load_rag_settings
from fakes.fake_knowledge_repo import FakeKnowledgeRepo
from fakes.fake_llm import FakeOpenAI, embedding_reply


def test_terms_match_with_and_without_diacritics():
    assert english_terms("Bảng băm chậm khi hàm băm kém") == ["hash table HashMap", "hash function hashCode"]
    assert english_terms("bang bam cham khi ham bam kem") == ["hash table HashMap", "hash function hashCode"]


def test_longest_phrase_wins_and_english_query_unchanged():
    assert english_terms("cập nhật đồng thời làm sai tồn kho") == [
        "concurrent update race condition lost update", "inventory stock"]
    assert expand_query("Distributed rate limiter with Redis") == "Distributed rate limiter with Redis"
    for noisy in ("Chất lượng mã và số lượng request", "Lưu lượng truy cập cao", "Lương kỳ vọng",
                  "Đánh giá và mở rộng giao diện, triển khai đồng thời"):
        assert english_terms(noisy) == [], noisy  # tu thong dung / trung sau khi bo dau: khong them nhieu
    assert english_terms("luồng xử lý chạy đa luồng") == ["thread", "multithreading thread"]


def test_retriever_embedding_usage_reaches_collector():
    client = FakeOpenAI([embedding_reply([[0.1] * 1536], prompt_tokens=12)])
    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), client, env={})
    retriever = build_retriever(load_rag_settings({"RAG_ENABLED": "1", "AI_DB_URL": "postgresql://x/y",
                                                   "RAG_QUERY_REWRITE": "0"}), gw)
    retriever._repo = FakeKnowledgeRepo()
    col = UsageCollector()
    asyncio.run(retriever.retrieve_for_topic(topic_id=None, category="Backend", difficulty=2,
                                             query="Bộ nhớ đệm", collector=col))
    assert col.to_metadata()["usage"]["embedding"]["input_tokens"] == 12
    assert client.calls[0]["input"] == ["Bộ nhớ đệm (cache)"]


def test_rewrite_combines_original_and_english_and_falls_back():
    from app.rag.retriever import Retriever
    from fakes.fake_knowledge_repo import FakeEmbed

    async def rewrite(q, collector=None):
        return "pagination offset slow last pages"

    async def broken(q, collector=None):
        return q  # QueryRewriter tra lai truy van goc khi LLM loi

    embed = FakeEmbed()
    r = Retriever(FakeKnowledgeRepo(), embed, rewrite=rewrite)
    asyncio.run(r.retrieve_for_topic(topic_id=None, category=None, difficulty=2, query="Phân trang chậm"))
    assert embed.queries == ["Phân trang chậm\npagination offset slow last pages"]
    assert asyncio.run(Retriever(FakeKnowledgeRepo(), embed, rewrite=broken).search_text("Phân trang chậm")) \
        == "Phân trang chậm (pagination offset limit)"


def test_query_rewriter_uses_llm_and_survives_errors():
    from app.rag.query_rewrite import QueryRewriter
    from fakes.fake_llm import reply, status_error

    client = FakeOpenAI([reply("hash table slow concurrent writes")])
    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), client, env={})
    col = UsageCollector()
    assert asyncio.run(QueryRewriter(gw).to_english("Bảng băm chậm", col)) == "hash table slow concurrent writes"
    assert '<untrusted label="query">' in client.calls[0]["messages"][1]["content"]
    assert col.to_metadata()["usage"]["query_rewriter"]["output_tokens"] == 5

    async def no_sleep(_):
        return None

    bad = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), FakeOpenAI([status_error(500)] * 3), env={},
                     sleep=no_sleep)
    assert asyncio.run(QueryRewriter(bad).to_english("Bảng băm chậm")) == "Bảng băm chậm"


def test_snippet_attach_has_deadline(monkeypatch):
    import app.plan_snippets as ps
    from app.mock_planner import build_plan, load_track
    from app.rag.retriever import Retriever
    from fakes.fake_knowledge_repo import FakeEmbed

    async def slow(*_a, **_k):
        await asyncio.sleep(1)
        return []

    plan = build_plan("java_backend", "junior", 20, None)
    r = Retriever(FakeKnowledgeRepo(), FakeEmbed())
    monkeypatch.setattr(r, "plan_snippets", slow)
    monkeypatch.setattr(ps, "SNIPPET_DEADLINE_S", 0.05)
    collector = UsageCollector()
    assert asyncio.run(ps.attach_reference_snippets(plan, load_track("java_backend"), r, collector)) is plan
    assert "rag_timeout" in collector.rag_errors


def test_copy_corpus_refuses_non_local_target(monkeypatch):
    import sys

    import pytest
    from evals import copy_corpus

    monkeypatch.setattr(sys, "argv", ["x", "--target", "postgresql://u:p@db.example.supabase.co:5432/postgres"])
    with pytest.raises(SystemExit, match="CUC BO"):
        copy_corpus.main()
