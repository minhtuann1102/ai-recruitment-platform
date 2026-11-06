"""Cau du phong khi LLM loi van phai doc duoc: focus la ca cau nen khong duoc de lai dau cau o giua cau mau."""
import pytest

from app.agents.interviewer import QuestionSpec, fallback_question
from app.models_interview import PlanTopic
from app.prompts.store import PromptStore

TOPIC = PlanTopic(id="t", title="Event loop", source="generic", objective="o", start_difficulty=2, opening_hint="h",
                  backup_question="b?", key_points=["a", "b", "c"])


@pytest.mark.parametrize("action", ["hint", "follow_up"])
@pytest.mark.parametrize("focus", ["Mô tả các pha của event loop.", "Lỗi async xử lý bằng try/catch..", "pha poll?"])
def test_focus_punctuation_does_not_break_the_sentence(action, focus):
    q = fallback_question(QuestionSpec(action=action, phase="technical", topic=TOPIC, difficulty=2, focus=focus))
    assert ".." not in q and ".?" not in q and "?." not in q and "??" not in q and q.endswith("?")


@pytest.mark.parametrize("focus", ["...", "?", " ", "…"])
def test_focus_of_only_punctuation_uses_the_topic(focus):
    q = fallback_question(QuestionSpec(action="hint", phase="technical", topic=TOPIC, difficulty=2, focus=focus))
    assert "Event loop" in q


def test_hint_keeps_a_sentence_focus_readable():
    q = fallback_question(QuestionSpec(action="hint", phase="technical", topic=TOPIC, difficulty=2,
                                       focus="Mô tả các pha của event loop."))
    assert ": Mô tả các pha của event loop." in q and "nghĩ tới Mô tả" not in q


def test_follow_up_does_not_glue_a_sentence_focus_into_the_template():
    q = fallback_question(QuestionSpec(action="follow_up", phase="technical", topic=TOPIC, difficulty=2,
                                       focus="Vì nó lấy snapshot của mảng khi tạo iterator."))
    assert ": Vì nó lấy snapshot của mảng khi tạo iterator." in q and "về Vì nó" not in q


def test_v5_is_the_default_prompt_and_v4_stays_available():
    store = PromptStore()
    assert store.get("interviewer").version == "v5" and store.get("interviewer", "v4").version == "v4"
