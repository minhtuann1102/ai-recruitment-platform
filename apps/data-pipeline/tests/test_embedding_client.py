"""T003 (spec 017): EmbeddingClient cong don response.usage.prompt_tokens vao total_tokens; client OpenAI gia, offline."""
from types import SimpleNamespace

import pytest

from pipeline import embedding_client
from pipeline.embedding_client import EmbeddingClient
from pipeline.settings import IndexSettings


class _FakeEmbeddings:
    def __init__(self, usages):
        self._usages = list(usages)
        self.calls = []

    def create(self, model, input):  # noqa: A002  (khop chu ky SDK)
        self.calls.append((model, list(input)))
        # tra ve nguoc thu tu index de kiem embed() sap lai dung
        data = [SimpleNamespace(index=i, embedding=[float(i)]) for i in reversed(range(len(input)))]
        return SimpleNamespace(data=data, usage=self._usages.pop(0))


class _FakeOpenAI:
    usages: list = []
    last = None

    def __init__(self, **kwargs):
        self.embeddings = _FakeEmbeddings(type(self).usages)
        type(self).last = self


@pytest.fixture()
def make_client(monkeypatch):
    def factory(usages):
        _FakeOpenAI.usages = list(usages)
        monkeypatch.setattr(embedding_client, "OpenAI", _FakeOpenAI)
        settings = IndexSettings("key", "http://x", "openai/text-embedding-3-small", 1536, "postgresql://x")
        return EmbeddingClient(settings)

    return factory


def test_total_tokens_starts_at_zero(make_client):
    assert make_client([]).total_tokens == 0


def test_total_tokens_accumulates_prompt_tokens_across_calls(make_client):
    client = make_client([SimpleNamespace(prompt_tokens=10, total_tokens=10), SimpleNamespace(prompt_tokens=7, total_tokens=7)])
    client.embed(["a", "b"])
    client.embed(["c"])
    assert client.total_tokens == 17


def test_provider_without_usage_leaves_total_unchanged(make_client):
    client = make_client([None, SimpleNamespace(prompt_tokens=5), SimpleNamespace()])
    client.embed(["a"])  # usage = None
    assert client.total_tokens == 0
    client.embed(["b"])
    client.embed(["c"])  # usage khong co prompt_tokens
    assert client.total_tokens == 5


def test_embed_signature_and_order_unchanged(make_client):
    client = make_client([SimpleNamespace(prompt_tokens=3)])
    assert client.embed(["x", "y", "z"]) == [[0.0], [1.0], [2.0]]
    assert _FakeOpenAI.last.embeddings.calls == [("openai/text-embedding-3-small", ["x", "y", "z"])]
