"""Bang tra thuat ngu STT (NFR-AI-QUAL17): doi dung dang phien am, khong dong vao cau go tay. Khong goi LLM."""
import json
import unicodedata

from app.stt_terms import STT_TERMS, normalize_stt_terms
from evals.label_sheet import load_golden
from evals.stt_noise import STT_GOLDEN


def test_spoken_terms_become_written_terms_longest_first():
    out = normalize_stt_terms("con ca rừn hát mắp an toàn hơn hát mắp khi nhiều thờ rét cùng ghi")
    assert out == "ConcurrentHashMap an toàn hơn HashMap khi nhiều thread cùng ghi"
    assert normalize_stt_terms("Đốc Cơ chạy trên cu  bơ nét") == "Docker chạy trên Kubernetes"  # hoa, nhieu khoang


def test_only_whole_words_are_replaced():
    assert normalize_stt_terms("đê bêtông") == "đê bêtông"
    assert normalize_stt_terms("ăn mau rồi đi bi a") == "ăn mau rồi đi bi a"
    for typed in ("nuôi con bách thú", "nem gia va", "cu ki", "pai lai", "dây sơn", "in đích"):  # cum tieng Viet
        assert normalize_stt_terms(typed) == typed


def test_odd_unicode_case_folding_never_raises():
    # IGNORECASE khop "ſ" voi "s", "İ"/"ı" voi "i" nhung lower() khong tra ve khoa trong bang
    for text in ("ſin cờ rô nai", "İn tơ phây", "ın tơ phây"):
        assert normalize_stt_terms(text) == text


def test_every_variant_has_two_syllables_and_is_unique():
    variants = [v for vs in STT_TERMS.values() for v in vs]
    assert all(len(v.split()) >= 2 for v in variants)  # am tiet don trung tu tieng Viet thuong
    assert len(variants) == len({unicodedata.normalize("NFC", v) for v in variants})


def test_typed_golden_answers_are_unchanged():
    clean = [s["answer"] for s in load_golden()]
    assert [normalize_stt_terms(a) for a in clean] == clean


def test_decomposed_unicode_matches_too():
    assert normalize_stt_terms(unicodedata.normalize("NFD", "dùng rê đít")) == "dùng Redis"


def test_noisy_golden_contains_table_terms():
    # bang lay tu catalog va tu vung chung; ghi lai do phu tren bo nhieu de bao cao, khong ep bang khop bo nhieu
    rows = [json.loads(line) for line in STT_GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(normalize_stt_terms(r["answer"]) != r["answer"] for r in rows)
