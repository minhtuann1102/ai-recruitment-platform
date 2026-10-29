"""Phase 03b: tham chieu ben vung cho chunk (ref, title, url) -> Evaluation.sources -> study_plan.resources.
URL chi do code lay tu metadata DE; Reporter LLM chi chon id r1.. LLM gia, khong do chat luong."""
import asyncio
import json

from test_reporter import make, output, session  # noqa: F401  (fixture phien choi that qua API)

from app.agents.evaluator import EvaluationInput, EvaluatorOutputV4, postcheck
from app.models_interview import CitedSource, PlanTopic, SourceRef
from app.plan_snippets import attach_reference_snippets
from app.mock_planner import build_plan, load_track
from app.rag.retriever import Retriever
from app.report_resources import resource_catalog, topic_sources
from app.report_scoring import build_report
from app.source_refs import source_ref, title_of
from fakes.fake_knowledge_repo import FakeEmbed, FakeKnowledgeRepo, qa

KP = ["Index B-tree giúp tìm nhanh thay vì quét toàn bảng", "Index làm chậm thao tác ghi",
      "Composite index theo leftmost prefix"]


def test_source_ref_title_is_first_line_and_only_http_urls_kept():
    chunk = qa("de-qa-1", "t", "**HashMap** xử lý va chạm thế nào?\n\nDùng bucket ...")
    ref = source_ref(chunk.__class__(**{**chunk.__dict__, "source_url": "https://github.com/x/README.md"}))
    assert ref == SourceRef(ref="de-qa-1", title="HashMap xử lý va chạm thế nào?", url="https://github.com/x/README.md")
    bad = chunk.__class__(**{**chunk.__dict__, "source_url": "javascript:alert(1)"})
    assert source_ref(bad).url is None and title_of("\n\n# Tiêu đề\nnội dung") == "Tiêu đề"


def test_plan_stores_sources_in_snippet_order():
    plan = build_plan("java_backend", "junior", 20, None)
    t = next(t for ph in plan.phases for t in ph.topics if t.catalog_ref)
    chunks = [qa(f"de-qa-{i}", t.catalog_ref, f"Câu hỏi {i}?\n\nĐáp án {i}.", None) for i in (7, 3, 5)]
    repo = FakeKnowledgeRepo(by_topic=chunks)
    out = asyncio.run(attach_reference_snippets(plan, load_track("java_backend"), Retriever(repo, FakeEmbed())))
    got = next(x for ph in out.phases for x in ph.topics if x.id == t.id)
    assert len(got.reference_snippets) >= 2  # du nhieu chunk de kiem thu tu
    assert [s.ref for s in got.reference_sources] == [next(c.dedup_key for c in chunks if c.content == text)
                                                      for text in got.reference_snippets]


def test_urls_echoed_back_by_client_are_still_http_only():
    assert SourceRef(ref="x", title="t", url="javascript:alert(1)").url is None
    assert SourceRef(ref="x", title="t", url="https://ok.dev/a\n").url is None
    long_title = CitedSource(id="S1", ref="x", title="t" * 400, url="https://ok.dev/a", support="supported")
    assert long_title.title == "t" * 150 and long_title.url == "https://ok.dev/a"


def _inp(sources, turn_sources=(), ref=None):
    topic = PlanTopic(id="t1", title="Index", source="catalog", objective="o", key_points=KP, start_difficulty=2,
                      opening_hint="h", backup_question="b", reference_snippets=["A ...", "B ..."],
                      reference_sources=list(sources))
    return EvaluationInput(level="junior", phase="technical", topic=topic, difficulty=2, turn_kind="main",
                           turn_number=2, question="Index?", answer="DB dùng B-tree nên không phải quét cả bảng. "
                           "Index làm ghi nhanh hơn vì có sẵn chỗ.", reference_answer="Đáp án" if ref else "",
                           turn_snippets=["C ..."] if turn_sources else [], turn_sources=list(turn_sources),
                           reference_source=ref)


def _out(*covered):
    return EvaluatorOutputV4.model_validate({
        "answer_type": "answered", "covered": list(covered), "missing_points": [], "misconceptions": [],
        "follow_up_focus": None, "scores": {"technical_accuracy": 3, "completeness": 3, "extensibility": 2,
                                            "relevance": 3}})


GOOD = {"point": KP[0], "quote": "DB dùng B-tree nên không phải quét cả bảng", "support": "supported"}
WRONG = {"point": "Index làm ghi nhanh hơn", "quote": "Index làm ghi nhanh hơn vì có sẵn chỗ",
         "support": "contradicted"}


def test_evaluation_resolves_cited_ids_to_stable_refs_contradicted_first():
    a, b, c = (SourceRef(ref=f"de-qa-{i}", title=f"Câu {i}?", url=None) for i in "abc")
    r = SourceRef(ref="de-qa-r", title="Câu kho?")
    ev = postcheck(_out({**GOOD, "source_ids": ["S1", "S9"]}, {**WRONG, "source_ids": ["S3", "R"]}),
                   _inp([a, b], [c], r))
    assert [(s.id, s.ref, s.support) for s in ev.sources] == [("S3", "de-qa-c", "contradicted"),
                                                              ("R", "de-qa-r", "contradicted"),
                                                              ("S1", "de-qa-a", "supported")]
    # plan cu / interview-service bo reference_sources: id van hop le nhung khong co tham chieu -> bo qua
    assert postcheck(_out({**GOOD, "source_ids": ["S1"]}), _inp([])).sources == []


def _with_sources(req, topic_id, sources, score=None):
    turns = []
    for t in req.turns:
        if t.topic_id == topic_id and t.evaluation:
            update = {"sources": sources, **({"turn_score_10": score} if score is not None else {})}
            t = t.model_copy(update={"evaluation": t.evaluation.model_copy(update=update)})
        turns.append(t)
    return req.model_copy(update={"turns": turns})


def _cited(ref, support="supported", url=None):
    return CitedSource(id="S1", ref=ref, title=f"Tiêu đề {ref}", url=url, support=support)


def test_topic_sources_put_contradicted_first_and_dedupe_by_ref(session):  # noqa: F811
    topic_id = next(t.topic_id for t in session.turns if t.evaluation and t.phase == "technical")
    req = _with_sources(session, topic_id, [_cited("x"), _cited("y", "contradicted"), _cited("x")])
    assert [s.ref for s in topic_sources(req.turns, topic_id)] == ["y", "x"]
    cat = resource_catalog(req.turns, [topic_id])
    assert list(cat) == ["r1", "r2"] and cat["r1"]["title"] == "Tiêu đề y"


def test_mock_report_study_plan_gets_resources_of_weak_topic(session):  # noqa: F811
    topic = next(t for t in build_report(session)["topics"] if t["phase"] == "technical")
    # diem luot 2.0 -> topic yeu -> vao study_plan; tai lieu lay tu sources cua chinh cac luot do
    req = _with_sources(session, topic["topic_id"], [_cited("q1", url="https://github.com/x")], score=2.0)
    plans = {p["topic"]: p for p in build_report(req)["study_plan"]}
    assert plans[topic["title"]]["resources"] == [{"title": "Tiêu đề q1", "url": "https://github.com/x"}]


def test_llm_reporter_maps_resource_ids_and_never_takes_urls(session):  # noqa: F811
    topic_id = next(t.topic_id for t in session.turns if t.evaluation and t.phase == "technical")
    req = _with_sources(session, topic_id, [_cited("q1", url="https://github.com/x"), _cited("q2")])
    study = [{"topic": "Ôn lại index", "priority": "high", "actions": ["Đọc tài liệu", "Làm bài"],
              "resource_ids": ["r2", "r9", "https://evil.example", "r1"]}]
    reporter, client = make([output(req, study_plan=study)])
    rep = asyncio.run(reporter.report(req))
    assert rep["study_plan"][0]["resources"] == [{"title": "Tiêu đề q2", "url": None},
                                                 {"title": "Tiêu đề q1", "url": "https://github.com/x"}]
    sent = json.loads(client.calls[0]["messages"][1]["content"].split("\n", 1)[1].rsplit("\n", 1)[0])
    assert sent["resources"][0] == {"id": "r1", "topic_id": topic_id, "title": "Tiêu đề q1"}  # khong gui url


def test_topic_without_cited_sources_falls_back_to_plan_sources_after_cited(session):  # noqa: F811
    topic_id = next(t.topic_id for t in session.turns if t.evaluation and t.phase == "technical")
    plan_refs = [SourceRef(ref="p1", title="Câu của topic?", url="https://github.com/p"), SourceRef(ref="y", title="Y")]
    assert [s.ref for s in topic_sources(session.turns, topic_id, plan_refs)] == ["p1", "y"]  # khong trich: bu
    req = _with_sources(session, topic_id, [_cited("y", "contradicted")])
    assert [s.ref for s in topic_sources(req.turns, topic_id, plan_refs)] == ["y", "p1"]  # trich truoc, bo trung
