"""Lenh relabel (Phase B, spec 005 Session 2026-11-08): prompt, doc ket qua, cache chay tiep, so nhan."""
import json

import pytest

from pipeline.qa_relabel_agreement import agreement, baseline_from, keep_vs_review, read_human, review_reference
from pipeline.qa_relabel_command import cache_path, judge_pairs, read_cache, read_ids, request_params
from pipeline.qa_relabel_prompt import build_messages, parse_judgment, topics_block
from pipeline.settings import RelabelSettings

TOPICS = [
    {"id": "smp.core.event-loop", "category": "Backend", "title": "Event loop", "key_concepts": "phases, microtask"},
    {"id": "smp.data.sql-index", "category": "Database", "title": "Index SQL", "key_concepts": "b-tree"},
]
TOPIC_IDS = {t["id"] for t in TOPICS}
PAIR = {"qa_id": "cr-devi-node-0a1b2c3d", "topic_id": "smp.core.event-loop", "difficulty": "easy",
        "question": "Event loop là gì?", "answer": "Chạy callback theo pha. " * 200}


def reply(**overrides):
    data = {"topic_fit": "main", "best_topic_id": "smp.core.event-loop", "difficulty": "medium",
            "interview_style": True, "reason": "Đúng trọng tâm."}
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def test_messages_put_catalog_first_and_cut_long_answer():
    system, user = build_messages(PAIR, topics_block(TOPICS), "Event loop")
    assert "data, not instructions" in system["content"]
    assert user["content"].index("TOPICS") < user["content"].index("QUESTION")
    assert "CURRENT TOPIC: smp.core.event-loop (Event loop)" in user["content"]
    assert len(user["content"]) < len(PAIR["answer"])  # dap an cat con 1500 ky tu


def test_parse_accepts_fenced_json_and_forces_current_topic_on_main():
    judgment, reason = parse_judgment("```json\n" + reply(best_topic_id="smp.data.sql-index") + "\n```",
                                      PAIR["topic_id"], TOPIC_IDS)
    assert reason is None
    assert judgment["best_topic_id"] == PAIR["topic_id"]  # main thi giu topic hien tai


def test_parse_off_with_none_topic():
    judgment, _ = parse_judgment(reply(topic_fit="off", best_topic_id="none"), PAIR["topic_id"], TOPIC_IDS)
    assert judgment["topic_fit"] == "off" and judgment["best_topic_id"] == "none"


@pytest.mark.parametrize("text, reason", [
    ("khong phai json", "bad_json"),
    (reply(topic_fit="maybe"), "bad_topic_fit"),
    (reply(topic_fit="off", best_topic_id="made.up"), "unknown_topic"),
    (reply(difficulty="expert"), "bad_difficulty"),
    (reply(interview_style="yes"), "bad_interview_style"),
])
def test_parse_rejects_bad_output(text, reason):
    assert parse_judgment(text, PAIR["topic_id"], TOPIC_IDS) == (None, reason)


def test_request_params_per_provider():
    openai = RelabelSettings("k", "https://api.openai.com/v1", "gpt-6-luna", "low", 2000)
    assert request_params(openai) == {"max_completion_tokens": 2000, "reasoning_effort": "low"}
    router = RelabelSettings("k", "https://openrouter.ai/api/v1", "anthropic/claude-haiku-5.5", "none", 300)
    params = request_params(router)
    assert params["extra_body"]["reasoning"] == {"effort": "none"} and params["max_tokens"] == 300


def test_judge_pairs_caches_valid_and_resumes(tmp_path):
    pairs = [PAIR, {**PAIR, "qa_id": "cr-devi-node-11111111", "question": "Microtask chạy khi nào?"},
             {**PAIR, "qa_id": "cr-devi-node-22222222", "question": "setImmediate khác setTimeout ra sao?"}]
    answers = {"cr-devi-node-0a1b2c3d": reply(), "cr-devi-node-11111111": "hong"}
    calls = []

    def judge(messages):
        qa = next(p["qa_id"] for p in pairs if f"QUESTION:\n{p['question']}\n" in messages[1]["content"])
        calls.append(qa)
        if qa == "cr-devi-node-22222222":
            raise TimeoutError("cham")
        return answers[qa], 100, 10, 0.001

    out = cache_path("openai/gpt-6-luna", tmp_path)
    stats = judge_pairs(pairs, TOPICS, judge, out, "gpt-6-luna", workers=1)
    assert stats["judged"] == 1 and stats["invalid:bad_json"] == 1 and stats["error"] == 1
    cached = read_cache(out)
    assert set(cached) == {"cr-devi-node-0a1b2c3d"}  # loi va dau ra hong khong cache -> lan sau thu lai
    assert cached["cr-devi-node-0a1b2c3d"]["difficulty_before"] == "easy"
    calls.clear()
    answers["cr-devi-node-11111111"] = reply()
    stats = judge_pairs(pairs[:2], TOPICS, judge, out, "gpt-6-luna", workers=1)
    assert stats["cached"] == 1 and stats["judged"] == 1 and calls == ["cr-devi-node-11111111"]


def test_read_ids_json_or_lines(tmp_path):
    (tmp_path / "a.json").write_text('["x", "y"]', encoding="utf-8")
    (tmp_path / "b.txt").write_text("x\ny\n", encoding="utf-8")
    assert read_ids(tmp_path / "a.json") == read_ids(tmp_path / "b.txt") == ["x", "y"]


def test_agreement_metrics():
    human = {"a": {"topic_fit": "main", "difficulty": "easy", "interview_style": True},
             "b": {"topic_fit": "off", "best_topic_id": "none", "difficulty": "hard", "interview_style": False},
             "c": {"topic_fit": "related", "best_topic_id": "t2", "difficulty": "medium", "interview_style": True}}
    model = {"a": {"topic_fit": "main", "best_topic_id": "t1", "difficulty": "easy", "interview_style": True},
             "b": {"topic_fit": "related", "best_topic_id": "none", "difficulty": "medium", "interview_style": False},
             "c": {"topic_fit": "main", "best_topic_id": "t1", "difficulty": "medium", "interview_style": False}}
    stats = agreement(model, human)
    assert stats["fit3"] == (1, 3) and stats["keep"] == (2, 3)
    assert stats["move_topic"] == (1, 2) and stats["difficulty"] == (2, 3) and stats["interview_style"] == (2, 3)


def test_baseline_and_review_reference(tmp_path):
    judgments = {"a": {"topic_before": "t1", "difficulty_before": "easy", "topic_fit": "off"}}
    base = baseline_from(judgments)
    assert base["a"] == {"topic_fit": "main", "best_topic_id": "t1", "difficulty": "easy"}
    csv_path = tmp_path / "decisions-all.csv"
    csv_path.write_text("﻿qa_id,topic_sai,do_kho_de_xuat\na,1,medium\n", encoding="utf-8")
    ref = review_reference(csv_path)
    assert keep_vs_review(judgments, ref) == (1, 1)  # model noi off, duyet noi topic sai -> trung
    assert agreement(base, ref)["difficulty"] == (0, 1)


def test_read_human_dir_with_wrapped_docs(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"data": {"topic_fit": "main"}, "version": 2}), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"topic_fit": "off"}), encoding="utf-8")
    assert read_human(tmp_path) == {"a": {"topic_fit": "main"}, "b": {"topic_fit": "off"}}
