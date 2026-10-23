import unicodedata

from pipeline.text_cleaning import clean_text, normalize_for_compare


def test_nfd_and_nfc_inputs_clean_to_same_text():
    nfc = "Thuật toán idempotent là gì?"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfd != nfc
    assert clean_text(nfd) == clean_text(nfc) == nfc


def test_strips_leftover_html_and_entities_but_keeps_vietnamese():
    raw = "<p>Giải thích <strong>event loop</strong> &amp; microtask</p><br/>trong <code>Node.js</code>"
    # </p> + <br/> = hai lan xuong dong -> mot dong trong (toi da 1 dong trong)
    assert clean_text(raw) == "Giải thích event loop & microtask\n\ntrong Node.js"


def test_removes_control_chars_and_collapses_whitespace():
    raw = "  Câu\x00 hỏi​   có\t\tkhoảng   trắng \r\n\r\n\r\n\r\nDòng hai  "
    assert clean_text(raw) == "Câu hỏi có khoảng trắng\n\nDòng hai"


def test_keeps_code_untouched():
    raw = "Dùng `List<String>` và `a<b`:\n```jsx\nreturn <div>\n    <p>Hi</p>\n</div>;   \n```"
    cleaned = clean_text(raw)
    assert "`List<String>`" in cleaned and "`a<b`" in cleaned
    assert "```jsx\nreturn <div>\n    <p>Hi</p>\n</div>;\n```" in cleaned


def test_does_not_eat_uppercase_generics_in_prose():
    assert clean_text("Map<K, V> và Optional<T>") == "Map<K, V> và Optional<T>"


def test_normalize_for_compare_drops_diacritics_case_and_punctuation():
    assert normalize_for_compare("Đâu là   khác biệt giữa GET và POST?") == "dau la khac biet giua get va post"
    assert normalize_for_compare("dau la khac biet giua GET va POST") == "dau la khac biet giua get va post"
