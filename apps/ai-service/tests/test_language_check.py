"""Kiem ngon ngu dau ra (tieng Viet, giu thuat ngu tieng Anh): cau tieng Anh tron cau / khong dau bi bat,
chuoi thuat ngu va cau Viet xen thuat ngu khong bi bat."""
import pytest

from app.language_check import english_sentences, wrong_language
from evals.sim_language import language


@pytest.mark.parametrize("text", [
    "Can you explain how HashMap handles collisions in Java?",
    "Bạn làm tốt phần REST. However, you should review the transaction isolation levels.",
    "Ban co the giai thich cach HashMap xu ly collision khong?",
])
def test_flags_english_or_unaccented_sentences(text):
    assert wrong_language(text)


@pytest.mark.parametrize("text", [
    "Bạn có thể giải thích HashMap xử lý collision thế nào không?",
    "Giờ mình sang phần Spring IoC và Dependency Injection, bạn dùng constructor injection khi nào?",
    "CSR vs SSR vs SSG vs ISR", "list vs tuple vs set vs dict", "ConcurrentHashMap vs Hashtable?", "",
])
def test_vietnamese_with_english_terms_and_term_lists_pass(text):
    assert not wrong_language(text)


def test_sim_language_metric_counts_questions_report_and_points():
    ev = {"covered_points": ["Nêu được hashCode"], "missing_points": ["It does not mention the load factor at all"],
          "misconceptions": []}
    sessions = {"p": {"turns": [{"question": "HashMap resize khi nào?", "evaluation": ev},
                                {"question": "What is the load factor in a HashMap?", "evaluation": None}],
                      "report": {"overall": {"summary": "Nền tảng ổn."}, "strengths": [], "improvements": [],
                                 "study_plan": [], "topics": [], "turns": []}}}
    out = language(sessions)
    assert out["questions"] == {"total": 2, "wrong": 1, "rate": 0.5}
    assert out["report"]["wrong"] == 0 and out["evaluator_points"]["wrong"] == 1
    assert out["sessions_with_wrong_language"] == 1 and english_sentences(out["examples"]["questions"][0])
