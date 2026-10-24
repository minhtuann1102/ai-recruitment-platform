"""Cong cu Phase A (context/next-phase-plan.md): chi so van phong, bo cau hoi + phieu nguoi cham, LLM-judge."""
import asyncio
import json

import pytest

from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from evals.judge_interviewer import agreement, judge_items, summarize
from evals.label_sheet import blind_id
from evals.question_set import QUOTA, export_sheet, items_from_sessions, parse_sheet, stratified
from evals.sim_style import style
from fakes.fake_llm import FakeOpenAI, reply


def test_style_detects_template_length_and_openers():
    qs = ["Bạn có thể giải thích HashMap được không?", "Giờ mình sang phần Docker. Bạn có thể nói về image không?",
          "Giờ mình sang phần Git. Merge và rebase khác nhau ở đâu?", "Index giúp truy vấn nhanh hơn nhờ đâu?"]
    out = style(qs)
    assert out["template_rate"] == 0.5 and out["top_opener"] == "gio minh sang" and out["top_opener_share"] == 0.5
    assert out["within_limits"] == {"template_rate": False, "mean_words": True, "top_opener_share": False}
    assert style([])["questions"] == 0


def session(level_quality="junior-java-strong", n=8):
    plan = {"phases": [{"phase": "technical", "topics": [{"id": "t1", "title": "HashMap", "key_points": ["a"]}]}]}
    actions = ["ask_main", "follow_up", "hint", "ask_main", "follow_up", "hint", "ask_main", "wrap_up"][:n]
    turns = [{"turn_number": i + 1, "phase": "technical", "topic_id": "t1", "action": a, "difficulty": 2,
              "question": f"Câu {i}?", "answer": f"Trả lời {i}", "question_source": "ai"} for i, a in enumerate(actions)]
    return {level_quality: {"plan": plan, "turns": turns}}


def test_items_keep_previous_turn_only_for_non_main_and_skip_adversarial():
    items = items_from_sessions({**session(), **session("junior-java-average+rambling")})
    assert len(items) == 8 and all(i["id"].startswith("junior-java-strong#") for i in items)
    assert items[0]["prev_question"] == "" and items[1]["prev_question"] == "Câu 0?" and items[1]["prev_answer"]
    assert items[0]["topic"] == "HashMap" and items[0]["level"] == "junior"


def test_stratified_respects_quota():
    items = [{"id": f"x{i}", "level": lv, "action": a} for i, (lv, a) in enumerate(
        (lv, a) for lv in ("fresher", "junior", "middle", "senior")
        for a in ["ask_main"] * 9 + ["follow_up"] * 9 + ["hint"] * 9 + ["wrap_up"] * 2)]
    picked = stratified(items)
    assert len(picked) == 4 * sum(QUOTA.values()) == 60
    assert sum(1 for i in picked if i["level"] == "senior" and i["action"] == "hint") == QUOTA["hint"]


def test_sheet_roundtrip_is_blind_and_validates(tmp_path):
    items = items_from_sessions(session())
    sheet = tmp_path / "s.csv"
    export_sheet(items, sheet)
    text = sheet.read_text(encoding="utf-8")
    assert "junior-java-strong" not in text and "question_source" not in text  # an persona va nguon cau hoi
    rows = text.splitlines()
    first = rows[1].split(",")[0]
    filled = tmp_path / "f.csv"
    filled.write_text("id,level_fit,natural,action_ok\n" + f"{first},vua,4,y\n", encoding="utf-8")
    labels = parse_sheet(filled, {i["id"] for i in items})
    assert list(labels.values()) == [{"level_fit": "ok", "natural": 4, "action_ok": True}]
    assert blind_id(next(iter(labels))) == first
    bad = tmp_path / "b.csv"
    bad.write_text("id,level_fit,natural,action_ok\n" + f"{first},rat de,9,y\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_sheet(bad, {i["id"] for i in items})


def test_judge_items_summary_and_agreement():
    items = items_from_sessions(session(n=2))
    out = [{"level_fit": "ok", "natural": 7, "action_ok": True, "single_question": True, "leaks": False, "reason": "r"},
           {"level_fit": "too_easy", "natural": 3, "action_ok": False, "single_question": True, "leaks": False,
            "reason": "r"}]

    async def no_sleep(_):
        return None
    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), FakeOpenAI([reply(json.dumps(o)) for o in out]), env={},
                    sleep=no_sleep, rng=lambda: 0.0)
    results = asyncio.run(judge_items(items, gw, concurrency=1))
    assert results[items[0]["id"]]["natural"] == 5  # kep 1-5
    s = summarize(results, items)["all"]
    assert s["n"] == 2 and s["level_fit"]["too_easy"] == 0.5 and s["action_ok"] == 0.5
    human = {items[0]["id"]: {"level_fit": "ok", "natural": 4, "action_ok": True},
             items[1]["id"]: {"level_fit": "ok", "natural": 2, "action_ok": False}}
    assert agreement(results, human) == {"n": 2, "level_fit": 0.5, "natural_within_1": 1.0, "action_ok": 1.0}
    assert agreement(results, {}) == {"n": 0}
