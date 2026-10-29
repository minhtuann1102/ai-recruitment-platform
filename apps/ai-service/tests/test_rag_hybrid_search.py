"""Hybrid RAG Phase 01: BM25 trong bo nho, RRF co trong so, retriever hybrid (gop, chiu loi tung duong, cache vector)
va xep hang cau kho theo RRF tu trung + vector. Khong can DB that."""
import asyncio

import app.plan_snippets as ps
from app.llm.usage import UsageCollector
from app.rag import bm25_index
from app.rag.bm25_index import Bm25Index, Bm25Store, tokens
from app.rag.circuit_breaker import CircuitBreaker
from app.rag.hybrid_fusion import rrf
from app.rag.models import SearchFilters
from app.rag.question_bank import BankEntry, rank
from app.rag.repository import build_bank_sql
from app.rag.retriever import Retriever
from app.rag.settings import load_rag_settings
from tests.fakes.fake_knowledge_repo import FakeEmbed, FakeKnowledgeRepo, qa

TOPIC = "java.core.collections-hashmap"
ALL = SearchFilters(("interview_qa", "textbook"))


def run(coro):
    return asyncio.run(coro)


def test_tokens_keep_diacritics_drop_stopwords_and_add_syllable_pairs():
    # "vì", "sao", "của" la tu chuc nang: bo khoi token don, van nam trong cap am tiet
    assert tokens("Vì sao dữ liệu của HashMap") == ["dữ", "liệu", "hashmap", "vì_sao", "sao_dữ", "dữ_liệu",
                                                    "liệu_của", "của_hashmap"]


def test_bm25_rare_terms_beat_common_ones_and_long_chunks_do_not_dominate():
    filler = " ".join(["dữ liệu khi bị lỗi chậm"] * 300)  # chunk rat dai chua toan tu pho bien (nhu chunk 10k ky tu)
    docs = [qa("long", "t", content=filler),
            qa("idem", "t", content="Thiết kế API idempotent để không trừ tiền hai lần"),
            *[qa(f"n{i}", "t", content=f"Dữ liệu bị lỗi ở bước {i}") for i in range(20)]]
    top = Bm25Index(docs).search("dữ liệu bị trừ tiền hai lần, idempotent", ALL, 3)
    assert top[0].qa_id == "idem" and "long" not in [c.qa_id for c in top]


def test_bm25_applies_category_and_difficulty_filters():
    docs = [qa("a", "t", content="redis cache", category="Backend", difficulty="hard"),
            qa("b", "t", content="redis cache", category="DevOps"), qa("c", "t", content="redis cache")]
    out = Bm25Index(docs).search("redis", SearchFilters(("interview_qa",), "Backend", "medium"), 5)
    assert [c.qa_id for c in out] == ["c"]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_bm25_store_backs_off_after_failure_and_reloads_after_ttl():
    clock, calls = Clock(), []

    async def load():
        calls.append(clock.now)
        if len(calls) == 1:
            raise OSError("db down")
        return [qa("a", "t", content=f"redis v{len(calls)}")]

    store = Bm25Store(load, clock)

    async def scenario():
        for _ in range(2):  # lan 1 loi; lan 2 trong RETRY_AFTER_S: khong doc lai DB
            try:
                await store.index()
            except RuntimeError:
                pass
        clock.now += bm25_index.RETRY_AFTER_S + 1
        first = await store.index()
        clock.now += bm25_index.CORPUS_TTL_S + 1
        stale = await store.index()  # het TTL: tra index cu, nap lai o nen
        await asyncio.sleep(0.05)
        return first, stale, await store.index()

    first, stale, fresh = run(scenario())
    assert len(calls) == 3 and stale is first and fresh is not first


def test_rrf_rewards_chunks_found_by_several_lists_and_respects_weights():
    a, b, c = qa("a", TOPIC), qa("b", TOPIC), qa("c", TOPIC)
    fused = rrf([[a, b], [c, b], [b, b]])  # b o ca ba danh sach (trung trong mot danh sach chi tinh mot lan)
    assert [x.qa_id for x in fused] == ["b", "a", "c"]
    assert fused[0].score == round(1 / 62 + 1 / 62 + 1 / 61, 6)
    assert [x.qa_id for x in rrf([[a], [c]], [1.0, 0.5])] == ["a", "c"]  # tu khoa nhe hon vector


def test_bank_sql_adds_similarity_only_with_vector():
    sql, params = build_bank_sql("t", "m", "easy", 80)
    assert "NULL::float8" in sql and params == ["t", "m", "easy", 80]
    sql, params = build_bank_sql("t", "m", "easy", 80, [0.5, 0.25])
    assert "q.embedding <=> %s::vector" in sql and params[0] == "[0.5,0.25]" and params[1:] == ["t", "m", "easy", 80]


def _hybrid(repo, embed=None, rewrite=None):
    return Retriever(repo, embed or FakeEmbed(), hybrid=True, rewrite=rewrite)


def retrieve(r, collector=None, **kw):
    args = {"topic_id": TOPIC, "category": "Backend", "difficulty": 3, "query": "Backend | HashMap | băm",
            "collector": collector}
    return run(r.retrieve_for_topic(**{**args, **kw}))


def test_hybrid_fuses_topic_lexical_and_vector():
    # q2 lech topic_id (DE gan sai) nhung khop ca tu khoa va vector -> vuot q1 chi co trong danh sach topic
    repo = FakeKnowledgeRepo(by_topic=[qa("q1", TOPIC)], hits=[qa("q2", "other"), qa("q3", "other")],
                             lexical=[qa("q2", "other", content="HashMap băm va chạm"), qa("z", "o", content="khác")])
    out = retrieve(_hybrid(repo))
    assert [c.qa_id for c in out] == ["q2", "q1", "q3"]
    assert {c[0] for c in repo.calls} == {"topic", "corpus", "search"}  # chay ca ba, khong chi khi thieu hit


def test_hybrid_keeps_working_when_one_path_fails():
    repo = FakeKnowledgeRepo(by_topic=[qa("q1", TOPIC)], hits=[qa("q2", "x")], lexical_fail=OSError())
    collector = UsageCollector()
    assert [c.qa_id for c in retrieve(_hybrid(repo), collector)] == ["q1", "q2"]
    assert collector.rag_errors == ["rag_hybrid_partial"]


def test_hybrid_all_paths_failing_returns_empty_and_reports_error():
    collector = UsageCollector()
    assert retrieve(_hybrid(FakeKnowledgeRepo(fail=OSError())), collector) == []
    assert collector.rag_errors == ["rag_retrieve_failed"]


def test_snippet_and_bank_share_one_rewrite_and_embed():
    rewrites = []

    async def rewrite(query, collector=None):
        rewrites.append(query)
        return "hash table HashMap"

    class BankRepo(FakeKnowledgeRepo):
        async def list_bank(self, topic_id, difficulty, limit, vector=None):
            self.calls.append(("bank", vector is not None))
            return [BankEntry("b1", "HashMap hoạt động thế nào?", "medium", "pair", similarity=0.8)]

    repo, embed = BankRepo(), FakeEmbed()
    r = _hybrid(repo, embed, rewrite)
    query = "Backend | HashMap | băm"

    async def both():
        return await asyncio.gather(
            r.retrieve_for_topic(topic_id=TOPIC, category="Backend", difficulty=3, query=query),
            r.bank_for_topic(TOPIC, 3, ["HashMap"], query=query))

    _, bank = run(both())
    assert [e.qa_id for e in bank] == ["b1"] and ("bank", True) in repo.calls
    assert rewrites == [query] and len(embed.queries) == 1


def test_bank_rank_uses_vector_similarity_as_tiebreak_signal():
    def e(qa_id, sim):
        return BankEntry(qa_id, "HashMap xử lý va chạm thế nào?", "medium", "p", similarity=sim)

    assert [x.qa_id for x in rank([e("a", 0.2), e("b", 0.9)], ["HashMap va chạm"], "medium", 2)] == ["b", "a"]
    assert [x.qa_id for x in rank([e("a", None), e("b", None)], ["HashMap va chạm"], "medium", 2)] == ["a", "b"]


def test_partial_error_is_degraded_and_does_not_trip_breaker(monkeypatch):
    breaker = CircuitBreaker(60)
    monkeypatch.setattr(ps, "_loaded", True)
    monkeypatch.setattr(ps, "_retriever", object())
    monkeypatch.setattr(ps, "_config_error", None)
    monkeypatch.setattr(ps, "_breaker", breaker)
    collector = UsageCollector()
    collector.rag_error("rag_hybrid_partial")
    assert ps.rag_status(collector)["status"] == "degraded"
    ps.note_rag_errors(collector)
    assert not breaker.is_open()


def test_hybrid_setting_default_on():
    url = {"AI_DB_URL": "postgresql://ro@h/ai_db"}
    assert load_rag_settings(url).hybrid and not load_rag_settings({**url, "RAG_HYBRID": "false"}).hybrid


def test_failed_rewrite_is_not_cached():
    calls = []

    async def rewrite(query, collector=None):
        calls.append(query)
        return query if len(calls) == 1 else "hash table"  # lan dau loi (tra nguyen truy van)

    r, embed = _hybrid(FakeKnowledgeRepo(), rewrite=rewrite), FakeEmbed()
    r.hybrid._embed = embed
    run(r.hybrid.query_vector("bảng băm"))
    run(r.hybrid.query_vector("bảng băm"))
    run(r.hybrid.query_vector("bảng băm"))  # lan 2 thanh cong da duoc cache
    assert len(calls) == 2 and embed.queries[-1] == "bảng băm\nhash table"


def test_timeout_of_one_request_does_not_cancel_shared_vector():
    gate = asyncio.Event()

    async def slow_embed(text, collector=None):
        await gate.wait()
        return [0.1] * 1536

    r = _hybrid(FakeKnowledgeRepo(), embed=slow_embed)

    async def scenario():
        a = asyncio.ensure_future(asyncio.wait_for(r.hybrid.query_vector("q"), timeout=0.01))
        b = asyncio.ensure_future(r.hybrid.query_vector("q"))
        try:
            await a
        except asyncio.TimeoutError:
            pass
        gate.set()
        return await b

    assert len(run(scenario())) == 1536


def test_embed_failure_still_returns_bm25_hits_as_degraded():
    collector = UsageCollector()
    r = _hybrid(FakeKnowledgeRepo(lexical=[qa("k", "o", content="HashMap băm")]), embed=FakeEmbed(fail=OSError()))
    out = run(r.retrieve_for_topic(topic_id=None, category="Backend", difficulty=3, query="HashMap băm",
                                   collector=collector))
    assert [c.qa_id for c in out] == ["k"] and collector.rag_errors == ["rag_hybrid_partial"]


def test_only_topic_path_failing_is_partial():
    class TopicFails(FakeKnowledgeRepo):
        async def list_by_topic_id(self, *a):
            raise OSError()

    collector = UsageCollector()
    out = retrieve(_hybrid(TopicFails(hits=[qa("q2", "x")])), collector)
    assert [c.qa_id for c in out] == ["q2"] and collector.rag_errors == ["rag_hybrid_partial"]


def test_slow_rewrite_embed_returns_topic_and_bm25_within_budget_then_caches(monkeypatch):
    from app.rag import hybrid_search
    monkeypatch.setattr(hybrid_search, "RESOLVE_BUDGET_S", 0.05)
    gate, embeds = asyncio.Event(), []

    async def slow_embed(text, collector=None):
        embeds.append(text)
        await gate.wait()
        return [0.1] * 1536

    repo = FakeKnowledgeRepo(by_topic=[qa("q1", TOPIC)], hits=[qa("q2", "x")],
                             lexical=[qa("k", "o", content="HashMap băm")])
    r, collector = _hybrid(repo, embed=slow_embed), UsageCollector()

    async def scenario():
        first = await r.retrieve_for_topic(topic_id=TOPIC, category="Backend", difficulty=3,
                                           query="Backend | HashMap | băm", collector=collector)
        gate.set()
        await asyncio.sleep(0.01)  # task embed dung chung chay xong va vao cache
        return first, await r.hybrid.query_vector("Backend | HashMap | băm")

    first, vector = run(scenario())
    assert {c.qa_id for c in first} == {"q1", "k"} and collector.rag_errors == ["rag_hybrid_partial"]
    assert len(vector) == 1536 and len(embeds) == 1


def test_bm25_store_skips_reload_when_corpus_unchanged_and_retries_failed_refresh_later():
    clock, loads, versions = Clock(), [], iter(["v1", "v1", OSError("db"), "v2"])

    async def load():
        loads.append(clock.now)
        return [qa("a", "t", content=f"redis v{len(loads)}")]

    async def version():
        v = next(versions)
        if isinstance(v, Exception):
            raise v
        return v

    store = Bm25Store(load, clock, version)

    async def refresh():
        clock.now += bm25_index.CORPUS_TTL_S + 1
        await store.index()
        await asyncio.sleep(0.05)

    async def scenario():
        first = await store.index()
        await refresh()  # v1 == v1: khong doc lai kho
        unchanged = await store.index()
        await refresh()  # dau van tay loi: giu index cu
        clock.now += 1
        await store.index()  # chua toi RETRY_AFTER_S: khong thu lai
        await asyncio.sleep(0.05)
        clock.now += bm25_index.RETRY_AFTER_S
        await store.index()  # v2: doc lai
        await asyncio.sleep(0.05)
        return first, unchanged, await store.index()

    first, unchanged, changed = run(scenario())
    assert unchanged is first and changed is not first and len(loads) == 2


def test_bm25_first_load_survives_version_failure_and_hung_load_resets(monkeypatch):
    async def version():
        raise OSError("md5 scan failed")

    async def load():
        return [qa("a", "t", content="redis")]

    assert run(Bm25Store(load, Clock(), version).index()).chunks[0].qa_id == "a"

    monkeypatch.setattr(bm25_index, "LOAD_TIMEOUT_S", 0.01)
    clock = Clock()

    async def hang():
        await asyncio.sleep(10)

    store = Bm25Store(hang, clock)

    async def scenario():
        try:
            await store.index()
        except RuntimeError:
            pass
        return store._task

    assert run(scenario()) is None  # task reset: lan sau (sau RETRY_AFTER_S) thu lai duoc
