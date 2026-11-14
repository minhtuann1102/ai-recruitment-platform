"""Scenario nhan them category `System Design` (phase 01 agentic): BM25 + SQL + start + turn; technical khong doi."""
import asyncio
import time

from app import plan_snippets as ps
from app.mock_planner import build_plan, load_track
from app.plan_snippets import scenario_categories
from app.rag.bm25_index import Bm25Index
from app.rag.models import Chunk, SearchFilters, category_matches
from app.rag.repository import build_search_sql
from app.rag.retriever import Retriever
from app.turn_reference_snippets import _filters, turn_snippets
from tests.fakes.fake_knowledge_repo import FakeEmbed, FakeKnowledgeRepo

DESIGN = ("Thiết kế hệ thống > Caching\nCache aside đọc từ cache trước, trượt thì đọc database rồi nạp lại cache, "
          "cần TTL và chiến lược vô hiệu hóa.")
BACKEND = "Backend > Servlet\nServlet container quản lý vòng đời servlet và thread pool xử lý request."
FRONTEND = "Frontend > Caching\nCache aside trên trình duyệt dùng service worker."


def book(cid: str, category: str, content: str) -> Chunk:
    return Chunk(id=cid, content=content, source_type="textbook", topic_id=None, category=category,
                 difficulty=None, qa_id=None, chunk_type=None, score=0.5)


CORPUS = [book("d", "System Design", DESIGN), book("b", "Backend", BACKEND), book("f", "Frontend", FRONTEND)]


def scenario_topic(track="java_backend"):
    plan = build_plan(track, "junior", 20, None)
    return next(t for ph in plan.phases if ph.phase == "scenario" for t in ph.topics)


def test_scenario_categories_main_plus_system_design():
    for track in ("java_backend", "nodejs_backend"):
        assert scenario_categories(load_track(track)) == ("Backend", "System Design")


def test_category_matches_single_and_multi():
    assert category_matches(SearchFilters(), "X") and category_matches(SearchFilters(), None)
    assert category_matches(SearchFilters(category="Backend"), "Backend")
    assert not category_matches(SearchFilters(category="Backend"), "System Design")
    multi = SearchFilters(categories=("Backend", "System Design"))
    assert category_matches(multi, "System Design") and not category_matches(multi, "Frontend")
    assert not category_matches(multi, None)


def test_bm25_finds_system_design_only_with_categories():
    index = Bm25Index(CORPUS)
    query = "cache aside TTL database"
    old = index.search(query, SearchFilters(("textbook",), "Backend"), 5)
    assert "d" not in {c.id for c in old}
    new = index.search(query, SearchFilters(("textbook",), categories=("Backend", "System Design")), 5)
    assert [c.id for c in new][0] == "d" and "f" not in {c.id for c in new}


def test_sql_single_element_unchanged_and_categories_added():
    old_sql, old = build_search_sql([1.0], SearchFilters(("textbook",), "Backend"), "m", 5)
    assert "category = %s" in old_sql and "category = ANY" not in old_sql
    sql, params = build_search_sql([1.0], SearchFilters(("textbook",), categories=("Backend", "System Design")),
                                   "m", 5)
    assert "category = ANY(%s)" in sql and ["Backend", "System Design"] in params
    assert sql.count("%s") == len(params)
    bare_sql, bare = build_search_sql([1.0], SearchFilters(), "m", 5)
    assert "category = " not in bare_sql and bare_sql.count("%s") == len(bare)


def test_start_scenario_passes_both_categories_to_search():
    repo = FakeKnowledgeRepo(hits=[CORPUS[0]])
    retriever = Retriever(repo, FakeEmbed(), textbook=True)
    out = asyncio.run(ps._snippets(retriever, "scenario", scenario_topic(), load_track("java_backend")))
    assert [c.id for c in out] == ["d"]
    filters = next(c[1] for c in repo.calls if c[0] == "search")
    assert filters.categories == ("Backend", "System Design") and filters.category is None
    assert filters.source_types == ("textbook",)


def test_turn_scenario_bm25_finds_system_design_and_technical_unchanged():
    repo = FakeKnowledgeRepo(lexical=CORPUS)
    retriever = Retriever(repo, FakeEmbed(), hybrid=True, turn_retrieval=True)
    retriever.textbook = True
    retriever.hybrid.bm25._index, retriever.hybrid.bm25._loaded_at = Bm25Index(CORPUS), time.monotonic()
    got = asyncio.run(turn_snippets(retriever, "java_backend", phase="scenario", topic=scenario_topic(),
                                    difficulty=2, question="Cache aside hoạt động ra sao?",
                                    answer="đọc cache trước, trượt thì đọc database, cần TTL", has_answer_key=False))
    assert DESIGN in got.texts and FRONTEND not in got.texts
    technical = next(t for ph in build_plan("java_backend", "junior", 20, None).phases if ph.phase == "technical"
                     for t in ph.topics if t.catalog_ref)
    flt = _filters(retriever, "technical", technical, load_track("java_backend"))
    assert flt.categories == () and flt.category is not None
