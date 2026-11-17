"""T016: cat section thanh doan (research R6) — kich thuoc, khong mat cau, khoi code, chu hoa/thuong."""
import re

from pipeline.textbook_chunker import (
    HARD_MAX_CHARS,
    chunk_page,
    render_content,
    split_fenced_blocks,
)


def _sentences(start: int, count: int) -> str:
    return " ".join(f"Sentence {i} explains how the Write-Ahead Log keeps data safe." for i in range(start, start + count))


def _page(*sections):
    return {"title": "PostgreSQL", "sections": [{"heading_path": h, "text": t} for h, t in sections]}


def _norm(text: str) -> str:
    return " ".join(text.split())


def test_short_section_kept_as_one_chunk():
    text = _sentences(1, 3)
    chunks = chunk_page(_page((["WAL"], text)))
    assert chunks == [{"heading_path": ["WAL"], "body": text}]


def test_empty_section_skipped_and_short_one_not_dropped():
    chunks = chunk_page(_page((["A"], "   \n"), (["B"], "Tiny.")))
    assert chunks == [{"heading_path": ["B"], "body": "Tiny."}]  # too_short la viec cua noise filter


def test_long_section_split_within_hard_max_and_no_sentence_lost():
    paragraphs = [_sentences(1, 4), _sentences(5, 4), _sentences(9, 30), _sentences(39, 4)]  # doan 3 > 1.600 ky tu
    text = "\n\n".join(paragraphs)
    assert len(paragraphs[2]) > HARD_MAX_CHARS
    chunks = chunk_page(_page((["Storage", "WAL"], text)))
    assert len(chunks) > 1
    assert all(len(c["body"]) <= HARD_MAX_CHARS for c in chunks)
    assert all(c["heading_path"] == ["Storage", "WAL"] for c in chunks)
    rejoined = " ".join(c["body"] for c in chunks)
    assert _norm(rejoined) == _norm(text)
    for i in range(1, 43):  # moi cau xuat hien dung mot lan, khong mat, khong lap
        assert len(re.findall(rf"Sentence {i} explains", rejoined)) == 1


def test_section_of_5000_chars_gives_many_chunks_under_hard_max():
    text = "\n\n".join(_sentences(i * 8, 8) for i in range(11))
    assert 5000 <= len(text) <= 9000
    chunks = chunk_page(_page((["Big"], text)))
    assert len(chunks) >= 4
    assert all(len(c["body"]) <= HARD_MAX_CHARS for c in chunks)
    assert _norm(" ".join(c["body"] for c in chunks)) == _norm(text)


def test_code_block_stays_with_preceding_paragraph():
    code = "```sql\nSELECT 1;\n\nSELECT 2;\n```"  # co dong trong ben trong khoi
    filler = "\n\n".join(_sentences(i * 5, 5) for i in range(1, 4))
    intro = "Run the following statement to check the Replication slot status. " * 2
    text = f"{filler}\n\n{intro.strip()}\n\n{code}\n\n{_sentences(100, 6)}"
    chunks = chunk_page(_page((["Replication"], text)))
    holder = [c["body"] for c in chunks if code in c["body"]]
    assert len(holder) == 1
    assert holder[0].index(intro.strip()) < holder[0].index(code)
    assert holder[0].index(code) - (holder[0].index(intro.strip()) + len(intro.strip())) == 2  # chi cach nhau mot dong trong


def test_fenced_split_keeps_blank_lines_inside_code():
    blocks = split_fenced_blocks("Intro text.\n\n```python\na = 1\n\nb = 2\n```\n\nAfter.")
    assert blocks == [("Intro text.", False), ("```python\na = 1\n\nb = 2\n```", True), ("After.", False)]


def test_oversize_code_block_split_into_fenced_pieces_within_hard_max():
    lines = "\n".join(f"line_{i} = compute({i})  # step {i}" for i in range(120))
    text = f"{_sentences(1, 4)}\n\n```python\n{lines}\n```"
    chunks = chunk_page(_page((["Code"], text)))
    assert len(chunks) > 1
    assert all(len(c["body"]) <= HARD_MAX_CHARS for c in chunks)
    joined = "\n".join(c["body"] for c in chunks)
    assert all(f"line_{i} = compute({i})" in joined for i in range(120))
    for c in chunks:  # khong co rao mo bi bo ngo
        assert c["body"].count("```") % 2 == 0


def test_single_long_sentence_without_punctuation_is_cut_on_whitespace():
    text = "alpha " * 700  # ~4.200 ky tu, khong dau cau
    chunks = chunk_page(_page((["Run-on"], text)))
    assert all(len(c["body"]) <= HARD_MAX_CHARS for c in chunks)
    assert _norm(" ".join(c["body"] for c in chunks)) == _norm(text)
    assert len(chunks) >= 4  # cat theo TARGET_MAX_CHARS, doan duoi nho gop lai chi khi van <= HARD_MAX_CHARS


def test_render_content_first_line_is_heading_path_and_case_preserved():
    body = "Call pg_stat_activity and ALTER SYSTEM SET work_mem; the VACUUM FULL command differs from vacuumdb."
    content = render_content("PostgreSQL", ["Monitoring", "Views"], body)
    assert content.split("\n")[0] == "PostgreSQL > Monitoring > Views"
    assert content == f"PostgreSQL > Monitoring > Views\n\n{body}"
    chunk = chunk_page(_page((["Monitoring", "Views"], body)))[0]
    assert chunk["body"] == body  # khong doi chu hoa/thuong ten ham, thuat ngu
    assert render_content("PostgreSQL", [], body).startswith("PostgreSQL\n\n")
