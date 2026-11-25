"""transcript_tokens (T018): chuan hoa, tach token, dem tu dem."""
import unicodedata

import pytest

from app.config import DEFAULT_FILLERS
from app.transcript_tokens import count_fillers, normalize, tokens


def fillers_in(text: str) -> int:
    return count_fillers(tokens(text), DEFAULT_FILLERS)


def test_tokens_lowercase_strip_punctuation_keep_vietnamese_diacritics():
    assert tokens("Ừm, HashMap không thread-safe, đúng không ạ?") == [
        "ừm", "hashmap", "không", "thread", "safe", "đúng", "không", "ạ"]


def test_nfd_input_is_normalised_to_nfc_before_matching():
    decomposed = unicodedata.normalize("NFD", "ừm kiểu như")
    assert decomposed != "ừm kiểu như"
    assert tokens(decomposed) == ["ừm", "kiểu", "như"]
    assert fillers_in(decomposed) == 3


@pytest.mark.parametrize("text,expected", [("ừm", 1), ("Ừm, à, ơ", 3), ("ờ để em nghĩ", 1), ("thì là", 2)])
def test_single_word_fillers(text, expected):
    assert fillers_in(text) == expected


def test_multi_word_filler_phrases_count_every_token():
    assert fillers_in("kiểu như là nói chung là ổn") == 5  # "kiểu như" 2 + "nói chung là" 3
    assert fillers_in("HashMap thì là không an toàn luồng") == 2


def test_trailing_a_particle_is_not_a_filler():
    assert fillers_in("Em hiểu rồi ạ") == 0
    assert fillers_in("Dạ vâng ạ.") == 0


def test_english_terms_and_text_without_fillers():
    assert tokens("CI/CD pipeline với Kubernetes") == ["ci", "cd", "pipeline", "với", "kubernetes"]
    assert fillers_in("Garbage collector dọn heap") == 0


def test_longest_phrase_wins_and_tokens_are_not_double_counted():
    assert count_fillers(tokens("nói chung là nói"), ["nói chung là", "nói chung", "là"]) == 3


def test_empty_and_punctuation_only_inputs():
    assert tokens("") == [] and tokens("  ... , ?? ") == []
    assert fillers_in("") == 0
    assert normalize("A-B/C_D") == "a b c d"
