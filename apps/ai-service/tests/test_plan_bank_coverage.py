"""Planner uu tien topic co cau trong kho o level dang hoi (Phase C muc 3). Kho gia, khong goi DB hay LLM."""
import asyncio
import time

import pytest

from app import mock_planner, plan_bank_coverage
from app.agents.planner import MockPlanner
from app.models_interview import StartRequest
from app.models_jd import JdProfile, JdRequirement
from app.plan_bank_coverage import bank_count, load_coverage, prefer_covered, settle, start_coverage
from app.rag.repository import COVERAGE_SQL, PgKnowledgeRepository
from app.rag.retriever import Retriever
from app.rag.settings import load_rag_settings
from app.turn_engine import start_session
from fakes.fake_knowledge_repo import FakeEmbed, FakeKnowledgeRepo

TRACK, LEVEL = "java_backend", "junior"
CATALOG = mock_planner.load_track(TRACK)


@pytest.fixture(autouse=True)
def fresh_cache():
    plan_bank_coverage._cache.clear()
    yield
    plan_bank_coverage._cache.clear()


def tech(plan):
    return [t for ph in plan.phases if ph.phase == "technical" for t in ph.topics]


def base_plan():
    return mock_planner.build_plan(TRACK, LEVEL, 30, None)  # thoi luong mac dinh cua StartRequest


def spare(plan, category):
    """Topic chua dung trong plan, theo nhom."""
    used = {t.catalog_ref for t in tech(plan)}
    return [t.id for t in CATALOG.topics_for(LEVEL) if t.id not in used and t.category == category]


def covered_all(plan, n=2, difficulty="easy"):
    return {t.catalog_ref: {difficulty: n} for t in tech(plan)}


def test_topic_without_bank_question_is_swapped_for_same_category_topic():
    plan = base_plan()
    first = tech(plan)[0]
    same, other = spare(plan, "Backend")[0], spare(plan, "Database")[0]
    coverage = {**covered_all(plan), first.catalog_ref: {}, same: {"easy": 2}, other: {"easy": 9}}
    out = prefer_covered(plan, CATALOG, LEVEL, coverage)
    swapped = tech(out)[0]
    assert swapped.catalog_ref == same and swapped.id == first.id
    assert swapped.start_difficulty == first.start_difficulty and swapped.source == "catalog"
    assert [t.catalog_ref for t in tech(out)[1:]] == [t.catalog_ref for t in tech(plan)[1:]]
    assert tech(plan)[0].catalog_ref == first.catalog_ref  # plan goc khong bi sua


def test_other_category_is_used_when_same_category_has_nothing():
    plan = base_plan()
    other = spare(plan, "Database")[0]
    coverage = {**covered_all(plan), tech(plan)[0].catalog_ref: {}, other: {"medium": 1}}
    assert tech(prefer_covered(plan, CATALOG, LEVEL, coverage))[0].catalog_ref == other


def test_questions_two_levels_away_do_not_count():
    plan = base_plan()  # junior bat dau o do kho 2 -> easy; cau hard lech 2 bac, question_bank.pick khong dung
    first = tech(plan)[0]
    assert bank_count({first.catalog_ref: {"hard": 5}}, first.catalog_ref, first.start_difficulty) == 0
    assert bank_count({first.catalog_ref: {"medium": 1, None: 2}}, first.catalog_ref, first.start_difficulty) == 3
    same = spare(plan, "Backend")[0]
    coverage = {**covered_all(plan), first.catalog_ref: {"hard": 5}, same: {"hard": 9}}
    assert tech(prefer_covered(plan, CATALOG, LEVEL, coverage))[0].catalog_ref == first.catalog_ref


def test_jd_topics_are_kept_even_without_bank_question():
    plan = base_plan()
    first = tech(plan)[0]
    coverage = {**covered_all(plan), first.catalog_ref: {}, spare(plan, "Backend")[0]: {"easy": 3}}
    out = prefer_covered(plan, CATALOG, LEVEL, coverage, keep=[first.catalog_ref])
    assert tech(out)[0].catalog_ref == first.catalog_ref


def test_plan_unchanged_without_coverage_or_candidates():
    plan = base_plan()
    assert prefer_covered(plan, CATALOG, LEVEL, {}) is plan
    coverage = {tech(plan)[0].catalog_ref: {"easy": 0}, tech(plan)[1].catalog_ref: {"easy": 1}}
    out = prefer_covered(plan, CATALOG, LEVEL, coverage)  # khong topic du phong nao co cau
    assert [t.catalog_ref for t in tech(out)] == [t.catalog_ref for t in tech(plan)]


def test_no_two_slots_get_the_same_replacement():
    plan = base_plan()
    refs = [t.catalog_ref for t in tech(plan)]
    only = spare(plan, "Backend")[0]
    coverage = {refs[0]: {}, refs[1]: {}, refs[2]: {"easy": 1}, only: {"easy": 4}}
    got = [t.catalog_ref for t in tech(prefer_covered(plan, CATALOG, LEVEL, coverage))]
    assert got.count(only) == 1 and len(set(got)) == len(got)


class CountRepo(FakeKnowledgeRepo):
    def __init__(self, coverage=None, fail=None, delay=0.0):
        super().__init__()
        self.coverage, self.count_fail, self.delay, self.counted = coverage or {}, fail, delay, 0

    async def count_bank(self, topic_ids):
        self.counted += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.count_fail:
            raise self.count_fail
        return {t: c for t, c in self.coverage.items() if t in topic_ids}


def test_coverage_is_cached_per_topic_set():
    repo, now = CountRepo({"a": {"easy": 1}}), [0.0]
    retr = Retriever(repo, FakeEmbed())
    clock = lambda: now[0]  # noqa: E731
    assert asyncio.run(load_coverage(retr, ["b", "a"], clock)) == {"a": {"easy": 1}}
    assert asyncio.run(load_coverage(retr, ["a", "b"], clock)) == {"a": {"easy": 1}} and repo.counted == 1
    now[0] = plan_bank_coverage.COVERAGE_TTL_S + 1
    asyncio.run(load_coverage(retr, ["a", "b"], clock))
    assert repo.counted == 2


def test_coverage_is_empty_when_rag_off_bank_off_or_failing(caplog):
    assert asyncio.run(load_coverage(None, ["a"])) == {}
    off = Retriever(CountRepo({"a": {"easy": 1}}), FakeEmbed(), question_bank=False)
    assert asyncio.run(load_coverage(off, ["a"])) == {}
    broken = Retriever(CountRepo(fail=RuntimeError("db")), FakeEmbed())
    assert asyncio.run(load_coverage(broken, ["a"])) == {} and "bank_coverage_failed" in caplog.text
    assert asyncio.run(load_coverage(Retriever(FakeKnowledgeRepo(), FakeEmbed()), ["a"])) == {}  # repo cu


def start(retr, **req):
    return asyncio.run(start_session(StartRequest(session_id="s", track=TRACK, level=LEVEL, **req),
                                     planner=MockPlanner(), retriever=retr))


def test_start_swaps_uncovered_topic_before_attaching_bank_questions():
    plan = base_plan()
    first, same = tech(plan)[0], spare(plan, "Backend")[0]
    coverage = {**covered_all(plan), first.catalog_ref: {}, same: {"easy": 2}}
    out = start(Retriever(CountRepo(coverage), FakeEmbed())).plan
    assert tech(out)[0].catalog_ref == same


def test_start_keeps_jd_must_topic():
    plan = base_plan()
    first, same = tech(plan)[0], spare(plan, "Backend")[0]
    jd = JdProfile(requirements=[JdRequirement(id="r1", text="HashMap", kind="must", topic_ids=[first.catalog_ref])])
    coverage = {**covered_all(plan), first.catalog_ref: {}, same: {"easy": 2}}
    out = start(Retriever(CountRepo(coverage), FakeEmbed()), jd_profile=jd).plan
    assert first.catalog_ref in [t.catalog_ref for t in tech(out)]


def test_slow_coverage_does_not_hold_start(monkeypatch):
    monkeypatch.setattr(plan_bank_coverage, "COVERAGE_WAIT_S", 0.05)
    plan = base_plan()
    coverage = {**covered_all(plan), tech(plan)[0].catalog_ref: {}, spare(plan, "Backend")[0]: {"easy": 2}}
    began = time.perf_counter()
    out = start(Retriever(CountRepo(coverage, delay=2.0), FakeEmbed())).plan
    assert time.perf_counter() - began < 1.0
    assert [t.catalog_ref for t in tech(out)] == [t.catalog_ref for t in tech(plan)]


def test_count_that_misses_the_wait_still_fills_the_cache(monkeypatch):
    monkeypatch.setattr(plan_bank_coverage, "COVERAGE_WAIT_S", 0.01)
    repo = CountRepo({"java.core.oop-solid": {"easy": 1}}, delay=0.05)

    async def go():
        task = start_coverage(Retriever(repo, FakeEmbed()), CATALOG, LEVEL)
        assert await settle(task) == {}
        await task
        return await load_coverage(Retriever(repo, FakeEmbed()), [t.id for t in CATALOG.topics_for(LEVEL)])

    assert asyncio.run(go()) == {"java.core.oop-solid": {"easy": 1}} and repo.counted == 1


def test_planner_error_still_fails_start_and_count_is_not_left_dangling():
    class Broken:
        async def plan(self, *a, **kw):
            raise RuntimeError("planner")

    with pytest.raises(RuntimeError):
        asyncio.run(start_session(StartRequest(session_id="s", track=TRACK, level=LEVEL), planner=Broken(),
                                  retriever=Retriever(CountRepo(delay=0.05), FakeEmbed())))


def test_repository_counts_spoken_questions_per_topic_and_difficulty():
    rows = [("java.a", "easy", 3), ("java.a", None, 1), ("java.b", "hard", 2)]

    class Conn:
        executed = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, sql, params):
            self.executed.append((sql, params))

            class Cur:
                async def fetchall(self):
                    return rows
            return Cur()

    conn = Conn()

    async def connect(dsn, **kw):
        return conn

    settings = load_rag_settings({"RAG_ENABLED": "1", "AI_DB_URL": "postgresql://ro@h/ai_db"})
    got = asyncio.run(PgKnowledgeRepository(settings, connect).count_bank(["java.a", "java.b"]))
    assert got == {"java.a": {"easy": 3, None: 1}, "java.b": {"hard": 2}}
    sql, params = conn.executed[0]
    assert sql == COVERAGE_SQL and params == ["text-embedding-3-small", ["java.a", "java.b"], 200]
