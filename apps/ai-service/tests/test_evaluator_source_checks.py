"""Phase 03a: Evaluator v4 trich nguon (S1.., R); code kiem id, contradicted -> misconception, confidence.
LLM gia, khong do chat luong cham."""
import app.agents.evaluator_provider as provider
from app.agents.evaluator import (EvaluationInput, EvaluatorOutput, EvaluatorOutputV4, build_messages, postcheck,
                                  uses_sources)
from app.evaluator_source_checks import (SourcedPoint, check_sources, confidence, merge_misconceptions,
                                         refuted_by_reference, restates_reference, source_blocks)
from app.models_interview import CitedSource, PlanTopic, SourceRef
from evals.run_evaluator_sourced import blocked_by_reference

KP = ["Index B-tree giúp tìm nhanh thay vì quét toàn bảng", "Index làm chậm thao tác ghi",
      "Composite index theo leftmost prefix"]
ANSWER = "DB dùng B-tree nên không phải quét cả bảng. Index làm ghi nhanh hơn vì có sẵn chỗ."


def topic(snippets=("Index B-tree ... (tài liệu)",)):
    return PlanTopic(id="t1", title="Index", source="catalog", objective="o", key_points=KP, start_difficulty=2,
                     opening_hint="h", backup_question="b", reference_snippets=list(snippets))


def inp(snippets=("Index B-tree ... (tài liệu)",), turn=(), ref=""):
    return EvaluationInput(level="junior", phase="technical", topic=topic(snippets), difficulty=2, turn_kind="main",
                           turn_number=2, question="Index?", answer=ANSWER, reference_answer=ref,
                           turn_snippets=list(turn))


def out(*covered, cls=EvaluatorOutputV4, misconceptions=()):
    return cls.model_validate({
        "answer_type": "answered", "covered": list(covered), "missing_points": [],
        "misconceptions": list(misconceptions), "follow_up_focus": None,
        "scores": {"technical_accuracy": 3, "completeness": 3, "extensibility": 2, "relevance": 3}})


GOOD = {"point": KP[0], "quote": "DB dùng B-tree nên không phải quét cả bảng", "source_ids": ["S1"],
        "support": "supported"}
WRONG = {"point": "Index làm ghi nhanh hơn", "quote": "Index làm ghi nhanh hơn vì có sẵn chỗ",
         "source_ids": ["s2"], "support": "contradicted"}


def test_ids_follow_prompt_order_topic_then_turn_then_reference():
    assert [i for i, _ in source_blocks(["a", "b"], "ref")] == ["S1", "S2", "R"]
    user = build_messages("SYS", inp(turn=["chunk lượt"], ref="đáp án"), with_ids=True)[1]["content"]
    assert "[S1] Index B-tree" in user and "[S2] chunk lượt" in user and "[R] đáp án" in user
    plain = build_messages("SYS", inp(turn=["chunk lượt"], ref="đáp án"))[1]["content"]
    assert "[S1]" not in plain and "đáp án" in plain  # v3: khong danh id


def test_unknown_ids_dropped_and_supported_without_valid_id_becomes_no_source():
    kept, refuted, invalid = check_sources([SourcedPoint("p", "q", ["S9", "R"], "supported")], ["S1"])
    assert refuted == [] and invalid == 2 and kept[0].support == "no_source" and kept[0].source_ids == []


def test_reference_answer_contradiction_becomes_misconception_and_caps_accuracy():
    ev = postcheck(out(GOOD, {**WRONG, "source_ids": ["R"]}), inp(ref="Index làm chậm thao tác ghi"))
    assert ev.covered_points == [KP[0]] and ev.misconceptions == [WRONG["quote"]]  # loi cua ung vien, khong phai point
    assert ev.scores.technical_accuracy == 1  # luat 4
    assert ev.evidence[0].source_ids == ["S1"] and ev.evidence[0].support == "supported"
    assert ev.confidence == "high"


def test_snippet_contradiction_is_not_credited_but_does_not_cap():
    # chunk BM25 chi gan dung chu de: khong tinh covered, nhung khong du de chan technical_accuracy
    ev = postcheck(out(GOOD, WRONG), inp(turn=["Index làm chậm thao tác ghi"]))
    assert ev.covered_points == [KP[0]] and ev.misconceptions == [] and ev.scores.technical_accuracy == 3


def test_misconceptions_put_code_checked_first_and_drop_near_duplicates():
    merged = merge_misconceptions(["Index làm ghi nhanh hơn"],
                                  ["Cho rằng index làm ghi nhanh hơn", "Cho rằng B-tree là hash", "Nghĩ index không tốn bộ nhớ"])
    assert merged == ["Index làm ghi nhanh hơn", "Cho rằng B-tree là hash", "Nghĩ index không tốn bộ nhớ"]
    ev = postcheck(out({**WRONG, "source_ids": ["R"]}, misconceptions=["Cho rằng B-tree là hash", "Nghĩ index không tốn bộ nhớ"]), inp(ref="đáp án"))
    assert ev.misconceptions[0] == WRONG["quote"]  # khong bi cat khi chi giu 2


def test_reference_only_turn_uses_r_and_rates_confidence():
    ev = postcheck(out({**GOOD, "source_ids": ["R"]}), inp(snippets=(), ref="đáp án"))
    assert ev.evidence[0].source_ids == ["R"] and ev.confidence == "high"


def test_version_parsing_and_bad_prompt_version_degrades_instead_of_500(monkeypatch):
    assert [uses_sources(v) for v in ("v1", "v2", "v3", "v4", "v10")] == [False, False, False, True, True]
    monkeypatch.setenv("AGENT_EVALUATOR_MODE", "llm")
    monkeypatch.setenv("EVALUATOR_PROMPT_VERSION", "v9")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setattr(provider, "_llm", None)
    assert isinstance(provider.get_evaluator(), provider.MockEvaluator)


def test_contradicted_without_valid_id_stays_covered_as_no_source():
    ev = postcheck(out({**WRONG, "source_ids": ["S7"]}), inp())
    assert ev.misconceptions == [] and ev.evidence[0].support == "no_source"


def test_confidence_low_when_sources_exist_but_nothing_supported_and_none_without_sources():
    unsupported = {**GOOD, "source_ids": [], "support": "no_source"}
    assert postcheck(out(unsupported), inp()).confidence == "low"
    no_docs = postcheck(out(GOOD), inp(snippets=()))
    assert no_docs.confidence is None and no_docs.evidence[0].support == "no_source"  # khong tai lieu: S1 la id la
    assert confidence([], True) is None


def test_v3_output_keeps_old_behaviour():
    v3 = {k: GOOD[k] for k in ("point", "quote")}
    ev = postcheck(out(v3, cls=EvaluatorOutput), inp())
    assert ev.confidence is None and ev.evidence[0].support is None and ev.evidence[0].source_ids == []


REFERENCE = ("Lớp java.lang.Throwable là lớp gốc của hệ thống phân cấp Exception trong Java. "
             "ConcurrentHashMap từ Java 8 khóa theo từng bucket, không khóa toàn bộ map trong mỗi lần ghi dữ liệu.")


def test_sentence_copied_from_reference_is_not_a_misconception():
    assert restates_reference("Lớp java.lang.Throwable là lớp gốc của hệ thống phân cấp Exception", REFERENCE)
    assert restates_reference("**Lớp java.lang.Throwable** là lớp gốc của hệ thống phân cấp Exception.", REFERENCE)


def test_real_misconceptions_survive_even_when_their_words_are_in_the_reference():
    assert not restates_reference("khóa toàn bộ map trong mỗi lần ghi dữ liệu", REFERENCE)  # R noi "khong khoa ..."
    assert not restates_reference("ConcurrentHashMap khóa toàn bộ map", REFERENCE)
    assert not restates_reference("lớp gốc là Throwable", REFERENCE)  # cum ngan
    assert not restates_reference("Lớp java.lang.Object là lớp gốc của hệ thống phân cấp Exception", REFERENCE)


def test_reference_that_debunks_a_sentence_never_counts_as_restating_it():
    wrong = "khóa toàn bộ map mỗi lần ghi"
    for ref in (f"Nó không phải {wrong}.", f"Nó không bao giờ {wrong}.", f"Nó doesn't {wrong}.",
                f"Sai lầm thường gặp: {wrong}.", f"Dùng bucket thay vì {wrong}.", f"Tránh {wrong}.",
                f"{wrong} là sai lầm phổ biến.", f"Trước Java 8 {wrong}, nay thì khác.",
                f"Hashtable {wrong}, còn ConcurrentHashMap không {wrong}."):
        assert not restates_reference(wrong, ref), ref


def test_pronoun_and_verb_are_not_mistaken_for_negation():
    # "no" va "chua" sau khi bo dau: fold bien "nó", "chứa" thanh tu phu dinh
    reference = "Cluster chứa nó, mỗi replica giữ một bản dữ liệu đầy đủ."
    assert restates_reference("mỗi replica giữ một bản dữ liệu đầy đủ", reference)


def test_refuted_text_is_what_the_candidate_said_not_the_correct_side():
    point = SourcedPoint("Dùng khóa theo bucket", "khóa cả map khi ghi", ["R"], "contradicted")
    assert refuted_by_reference([point], REFERENCE) == ["khóa cả map khi ghi"]


def test_point_copying_a_reference_sentence_is_not_a_refutation():
    copied = SourcedPoint("Lớp java.lang.Throwable là lớp gốc của hệ thống phân cấp Exception", "New Runnable Blocked",
                          ["R"], "contradicted")
    assert refuted_by_reference([copied], REFERENCE) == []


def test_reference_sentence_listed_as_misconception_does_not_cap_accuracy():
    ev = postcheck(out(GOOD, misconceptions=["Lớp java.lang.Throwable là lớp gốc của hệ thống phân cấp Exception"]),
                   inp(ref=REFERENCE))
    assert ev.misconceptions == [] and ev.scores.technical_accuracy == 3


def test_candidate_misconception_still_caps_accuracy_with_reference():
    ev = postcheck(out(GOOD, misconceptions=["Index làm ghi nhanh hơn"]), inp(ref=REFERENCE))
    assert ev.misconceptions == ["Index làm ghi nhanh hơn"] and ev.scores.technical_accuracy == 1


def test_refuted_point_keeps_the_cap_and_shows_the_candidate_words():
    wrong = {**WRONG, "point": "Index làm chậm ghi", "source_ids": ["R"]}  # point chep y dung cua R, ngan
    ev = postcheck(out(GOOD, wrong), inp(ref="Index làm chậm ghi."))
    assert ev.misconceptions == [WRONG["quote"]] and ev.scores.technical_accuracy == 1


def test_blocked_by_reference_needs_the_cap_to_have_run():
    ref = SourceRef(ref="q", title="q")
    ev = postcheck(out(GOOD), inp(ref=REFERENCE))
    cited = [CitedSource(**ref.model_dump(), id="R", support="contradicted")]
    assert not blocked_by_reference(ev.model_copy(update={"sources": cited}))
    assert blocked_by_reference(ev.model_copy(update={"sources": cited, "misconceptions": ["x"]}))
    assert not blocked_by_reference(ev.model_copy(update={"misconceptions": ["x"]}))
