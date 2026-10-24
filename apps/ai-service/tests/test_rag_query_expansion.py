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
    retriever = build_retriever(load_rag_settings({"RAG_ENABLED": "1", "AI_DB_URL": "postgresql://x/y"}), gw)
    retriever._repo = FakeKnowledgeRepo()
    col = UsageCollector()
    asyncio.run(retriever.retrieve_for_topic(topic_id=None, category="Backend", difficulty=2,
                                             query="Bộ nhớ đệm", collector=col))
    assert col.to_metadata()["usage"]["embedding"]["input_tokens"] == 12
    assert client.calls[0]["input"] == ["Bộ nhớ đệm (cache)"]
