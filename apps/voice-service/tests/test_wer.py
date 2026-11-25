"""evals/wer.py (T025): Levenshtein theo token, ty le loi am tiet, ty le nhan dung thuat ngu."""
import pytest

from evals.wer import edit_distance, syllable_error_rate, term_recognition, term_recognition_rate, term_vocabulary


@pytest.mark.parametrize("ref,hyp,expected", [
    ([], [], 0), (["a"], [], 1), ([], ["a", "b"], 2), (["a", "b", "c"], ["a", "b", "c"], 0),
    (["a", "b", "c"], ["a", "x", "c"], 1),  # thay
    (["a", "b", "c"], ["a", "c"], 1),  # xoa
    (["a", "c"], ["a", "b", "c"], 1),  # chen
    (["k", "i", "t", "t", "e", "n"], ["s", "i", "t", "t", "i", "n", "g"], 3)])
def test_edit_distance(ref, hyp, expected):
    assert edit_distance(ref, hyp) == expected
    assert edit_distance(hyp, ref) == expected  # doi xung


def test_syllable_error_rate_substitution_and_deletion():
    ref = "HashMap không an toàn luồng"  # 5 token
    assert syllable_error_rate(ref, ref) == 0.0
    assert syllable_error_rate(ref, "hashmap không an toàn") == pytest.approx(1 / 5)  # thieu 1
    assert syllable_error_rate(ref, "hash map không an toàn luồng") == pytest.approx(2 / 5)  # tach doi 1 + chen 1 -> 2 loi


def test_syllable_error_rate_ignores_case_and_punctuation_but_not_diacritics():
    assert syllable_error_rate("Ừm, HashMap không thread-safe.", "ừm hashmap không thread safe") == 0.0
    assert syllable_error_rate("không", "khong") == 1.0


def test_syllable_error_rate_can_exceed_one_and_rejects_empty_reference():
    assert syllable_error_rate("a", "a b c d") == 3.0
    with pytest.raises(ValueError):
        syllable_error_rate(" ... ", "a")


def test_term_vocabulary_splits_multiword_terms():
    assert term_vocabulary(["Spring Boot", "HashMap", "CI/CD"]) == {"spring", "boot", "hashmap", "ci", "cd"}


def test_term_recognition_counts_reference_terms_found_in_hypothesis():
    terms = ["HashMap", "ConcurrentHashMap", "Spring Boot"]
    ref = "HashMap khác ConcurrentHashMap trong Spring Boot"
    assert term_recognition(ref, ref, terms) == (4, 4)
    assert term_recognition(ref, "hash map khác concurrent hash map trong spring boot", terms) == (2, 4)
    assert term_recognition(ref, "", terms) == (0, 4)
    assert term_recognition_rate(ref, "hashmap khác trong spring", terms) == 0.5


def test_repeated_term_is_counted_per_occurrence():
    assert term_recognition("Kafka Kafka và Kafka", "kafka và kafka", ["Kafka"]) == (2, 3)


def test_reference_without_terms_has_no_rate():
    assert term_recognition("xin chào các bạn", "xin chào", ["HashMap"]) == (0, 0)
    assert term_recognition_rate("xin chào các bạn", "xin chào", ["HashMap"]) is None
    assert term_recognition_rate("HashMap", "hashmap", []) is None
