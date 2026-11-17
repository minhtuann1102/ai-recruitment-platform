"""pipeline/textbook_keyword_rank: tokenize cung quy tac ai-service, BM25 xep tai lieu chua dung thuat ngu len tren,
`allow` loc truoc khi cat k."""
from pipeline.textbook_keyword_rank import Bm25, tokenize


def _doc(text, category="Database"):
    return {"content": text, "metadata": {"category": category}}


def test_tokenize_lowercases_drops_short_and_stopwords_but_keeps_them_in_bigrams():
    assert tokenize("The Cache_Aside pattern") == ["cache", "aside", "pattern", "the_cache", "cache_aside", "aside_pattern"]
    assert tokenize("a B") == ["a_b"]  # token don < 2 ky tu bi bo, cap van con


def test_tokenize_keeps_vietnamese_diacritics_and_normalizes_nfc():
    # Dau roi (NFD) phai thanh cung token voi dang dung san (NFC), khong bi tach doi tu o dau thanh
    assert tokenize("Cách báo") == tokenize("Cách báo") == ["cách", "báo", "cách_báo"]


def test_doc_containing_term_ranks_above_doc_without_it():
    docs = [
        _doc("Replication copies data to follower nodes for durability."),
        _doc("Sharding splits a large table across many machines to spread write load."),
        _doc("Caching keeps hot rows in memory."),
    ]
    top = Bm25(docs).top("sharding table", 3)
    assert top[0] is docs[1] and docs[0] not in top  # doc khong chua tu nao khong vao ket qua


def test_rarer_term_outweighs_common_term():
    docs = [_doc("index index index index scan"), _doc("index tuning with partial predicate"), _doc("index basics")]
    assert Bm25(docs).top("index predicate", 1)[0] is docs[1]  # "predicate" chi co o mot doc -> IDF cao


def test_allow_filters_category_before_cutting_k():
    docs = [_doc("lock contention in postgres", "Database"), _doc("lock contention in spring", "Backend"),
            _doc("lock timeout tuning", "Database")]
    only_backend = Bm25(docs).top("lock", 1, allow=lambda d: d["metadata"]["category"] == "Backend")
    assert only_backend == [docs[1]]  # doc Backend van ra du xep sau doc Database neu khong loc
    assert Bm25(docs).top("lock", 5, allow=lambda d: False) == []


def test_k_is_respected_and_ties_keep_input_order():
    docs = [_doc("queue worker"), _doc("queue worker"), _doc("queue worker")]
    assert Bm25(docs).top("queue", 2) == [docs[0], docs[1]]


def test_plain_strings_and_custom_text_accessor_work():
    assert Bm25(["alpha beta gamma", "delta"]).top("gamma", 1) == ["alpha beta gamma"]
    pairs = [("x", "message broker"), ("y", "cache layer")]
    assert Bm25(pairs, text_of=lambda p: p[1]).top("broker", 1) == [pairs[0]]


def test_empty_corpus_and_unknown_query_return_nothing():
    assert Bm25([]).top("anything", 3) == []
    assert Bm25([_doc("alpha beta")]).top("zzz", 3) == []
