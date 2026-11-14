"""Topic du phong luc start (phase 05): chon theo catalog / kho / JD / CV, id alt{n}, keep_ids, gan cau kho, co tat."""
import asyncio

from app import mock_planner
from app.agents.planner import MockPlanner
from app.models_cv import CvProfile, CvSkill
from app.models_interview import StartRequest
from app.models_jd import JdProfile, JdRequirement
from app.plan_snippets import attach_reference_snippets
from app.replan_reserve import MAX_RESERVE, select_reserve, with_reserve
from app.turn_engine import start_session
from tests.test_question_bank import FakeRetriever

TRACK, LEVEL = "java_backend", "junior"
CATALOG = mock_planner.load_track(TRACK)
ALL_BANDS = {"easy": 2, "medium": 2, "hard": 2}


def plan(minutes=30, jd=None):
    return mock_planner.build_plan(TRACK, LEVEL, minutes, None, jd)


def tech(p):
    return [t for ph in p.phases if ph.phase == "technical" for t in ph.topics]


def spare_ids(p):
    used = {t.catalog_ref for t in tech(p)}
    return [t.id for t in CATALOG.topics_for(LEVEL) if t.id not in used]


def jd(*req):
    return JdProfile(requirements=[JdRequirement(id=f"r{i}", text="yc", kind=k, topic_ids=[t])
                                   for i, (k, t) in enumerate(req, 1)])


def test_reserve_is_up_to_two_unused_catalog_topics_with_alt_ids():
    p = plan()
    pool = select_reserve(p, CATALOG, LEVEL, {}, None, None)
    assert [t.id for t in pool.reserve] == ["alt1", "alt2"] and len(pool.reserve) <= MAX_RESERVE
    assert all(t.catalog_ref in spare_ids(p) and t.source == "catalog" for t in pool.reserve)
    ids = {t.id for ph in p.phases for t in ph.topics}
    assert not ids & {t.id for t in pool.reserve} and all(t.id.startswith("alt") for t in pool.reserve)
    assert pool.keep_ids == []  # khong co JD


def test_ids_never_collide_with_jd_requirement_ids():
    j = jd(("must", spare_ids(plan())[0]), ("nice", "x.y"))
    pool = select_reserve(plan(jd=j), CATALOG, LEVEL, {}, None, j)
    assert not {t.id for t in pool.reserve} & {r.id for r in j.requirements}


def test_keep_ids_are_plan_topics_mapped_from_jd_priority_requirements():
    first, second = tech(plan())[0].catalog_ref, tech(plan())[1].catalog_ref
    j = jd(("must", first), ("nice", second), ("must", "khong.co.trong.plan"))
    p = plan(jd=j)
    pool = select_reserve(p, CATALOG, LEVEL, {}, None, j)
    by_ref = {t.catalog_ref: t.id for t in tech(p)}
    assert set(pool.keep_ids) == {by_ref[first], by_ref[second]}


def test_jd_topic_outside_the_plan_ranks_first_and_cv_skills_do_not_break_ranking():
    p = plan()
    outside = spare_ids(p)[-1]
    assert select_reserve(p, CATALOG, LEVEL, {}, None, jd(("must", outside))).reserve[0].catalog_ref == outside
    cv = CvProfile(headline="Java dev", skills=[CvSkill(name="Java", category="language", evidence="work")])
    assert len(select_reserve(p, CATALOG, LEVEL, {}, cv, None).reserve) == 2


def test_known_bank_counts_require_questions_unknown_does_not():
    p = plan()
    spare = spare_ids(p)
    pool = select_reserve(p, CATALOG, LEVEL, {spare[3]: ALL_BANDS}, None, None)
    assert [t.catalog_ref for t in pool.reserve] == [spare[3]]
    assert len(select_reserve(p, CATALOG, LEVEL, {}, None, None).reserve) == 2  # rong = khong biet: khong loc
    assert select_reserve(p, CATALOG, LEVEL, {spare[0]: {}}, None, None) is None  # biet: khong topic nao co cau


def test_pool_of_zero_disables_replan_for_the_session(monkeypatch):
    p = plan()
    full = CATALOG.model_copy(update={"topics": [t for t in CATALOG.topics if t.id not in spare_ids(p)]})
    assert select_reserve(p, full, LEVEL, {}, None, None) is None
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    assert with_reserve(p, full, LEVEL, {}, None, None).replan is None


def test_flag_off_returns_the_same_plan_object(monkeypatch):
    monkeypatch.delenv("REPLAN_ENABLED", raising=False)
    p = plan()
    assert with_reserve(p, CATALOG, LEVEL, {}, None, None) is p
    monkeypatch.setenv("REPLAN_ENABLED", "true")  # rules: van tat
    monkeypatch.delenv("POLICY_MODE", raising=False)
    assert with_reserve(p, CATALOG, LEVEL, {}, None, None) is p


def run_start(**kw):
    return asyncio.run(start_session(StartRequest(session_id="s", track=TRACK, level=LEVEL, duration_minutes=30, **kw),
                                     planner=MockPlanner()))


def test_start_flag_off_is_identical_and_flag_on_only_adds_the_replan_key(monkeypatch):
    monkeypatch.delenv("REPLAN_ENABLED", raising=False)
    off = run_start()
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("REPLAN_ENABLED", "false")
    explicit_off = run_start()
    assert off.plan.replan is None and off.plan.model_dump() == explicit_off.plan.model_dump()
    assert off.state.model_dump() == explicit_off.state.model_dump() and off.state.swaps == []
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    on = run_start()
    assert on.plan.replan is not None
    assert {**on.plan.model_dump(), "replan": None} == off.plan.model_dump()  # chi them khoa replan
    assert on.state.model_dump() == off.state.model_dump()  # reserve khong vao state.topics


def test_start_stores_keep_ids_from_the_jd_in_the_plan(monkeypatch):
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    ref = tech(plan())[1].catalog_ref
    r = run_start(jd_profile=jd(("must", ref)))
    assert r.plan.replan.keep_ids == [next(t.id for t in tech(r.plan) if t.catalog_ref == ref)]


def with_pool(monkeypatch):
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    return with_reserve(plan(), CATALOG, LEVEL, {}, None, None)


def test_reserve_gets_bank_questions_in_the_same_reference_pass(monkeypatch):
    p = with_pool(monkeypatch)
    out = asyncio.run(attach_reference_snippets(p, CATALOG, FakeRetriever()))
    assert all(len(t.bank_questions) == 2 for t in out.replan.reserve)
    assert all(not t.bank_questions for t in p.replan.reserve)  # plan vao khong bi sua


def test_reference_pass_is_skipped_without_a_retriever(monkeypatch):
    p = with_pool(monkeypatch)
    assert asyncio.run(attach_reference_snippets(p, CATALOG, None)) is p
