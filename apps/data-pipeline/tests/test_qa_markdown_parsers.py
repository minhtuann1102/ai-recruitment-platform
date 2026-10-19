from crawlers.qa_markdown_parsers import parse_details
from crawlers.qa_sources import SOURCES
from pipeline.collect_command import collected_id, records_from_markdown, truncate_answer

PARSERS = {s.name: s for s in SOURCES}

DEVINTERVIEW_MD = """# 100 Java Questions
## 1. Explain _Write Once, Run Anywhere_ in **Java**.

Java compiles to bytecode that any JVM runs, see [docs](https://example.com).

### Code
```java
List<String> xs = new ArrayList<>();
```

## 2. What is the `__init__` of nothing?

Short answer that is long enough to keep around.

#### Explore all 100 answers here
<img src="x">
"""

LEARNING_ZONE_MD = """## Q. What is a closure? 👶

A closure keeps access to the outer scope after the outer function returns.

<div align="right">
    <b><a href="#table-of-contents">↥ back to top</a></b>
</div>

## # 2. SECTION

## Q. Short?
"""

SUDHEERJ_MD = """1.  ### What is React?

    React is a library for building user interfaces from components.

    **[⬆ Back to Top](#table-of-contents)**

2.  ### What is JSX?

    JSX lets you write `<div>` markup inside JavaScript code files.

### Coding Exercise

#### 1. What is the output of below code
"""

DETAILS_MD = """<details>
<summary>1. What is a Container?</summary><br><b>

A container packages an app with its dependencies in an isolated process.
</b></details>
<details>
<summary>Empty one?</summary><br><b>
</b></details>
"""


def test_devinterview_headings_stop_at_footer_and_clean_question():
    pairs = PARSERS["devi-java"].parse(DEVINTERVIEW_MD)
    assert [q for q, _ in pairs] == ["Explain Write Once, Run Anywhere in Java.", "What is the `__init__` of nothing?"]
    assert "List<String>" in pairs[0][1] and "docs" in pairs[0][1] and "example.com" not in pairs[0][1]
    assert "Explore all" not in pairs[1][1] and "img" not in pairs[1][1]


def test_learning_zone_drops_back_to_top_footer_and_emoji():
    pairs = PARSERS["lz-java-basics"].parse(LEARNING_ZONE_MD)
    assert pairs[0] == ("What is a closure?", "A closure keeps access to the outer scope after the outer function returns.")


def test_sudheerj_dedents_answers_and_stops_at_coding_exercise():
    pairs = PARSERS["sudheerj-react"].parse(SUDHEERJ_MD)
    assert [q for q, _ in pairs] == ["What is React?", "What is JSX?"]
    assert pairs[0][1] == "React is a library for building user interfaces from components."
    assert "Coding Exercise" not in pairs[1][1] and "output of below" not in pairs[1][1]


def test_details_parser_strips_numbering_and_tags():
    pairs = parse_details(DETAILS_MD)
    assert pairs[0][0] == "What is a Container?"
    assert "isolated process" in pairs[0][1]


def test_records_skip_short_answers_scrub_pii_and_get_stable_ids():
    source = PARSERS["devops-exercises"]
    md = DETAILS_MD.replace("isolated process.", "isolated process. Mail ops@corp.vn for help.")
    records = records_from_markdown(source, "topics/containers/README.md", md, "2026-10-19T00:00:00+00:00")
    assert len(records) == 1  # "Empty one?" bi loai vi dap an rong
    record = records[0]
    assert "[email]" in record["answer"] and "ops@corp.vn" not in record["answer"]
    assert record["cid"] == collected_id("devops-exercises", record["source_url"], record["question"])
    assert record["cid"].startswith("cr-devops-exercises-") and len(record["cid"].split("-")[-1]) == 8


def test_truncate_answer_cuts_at_paragraph_and_closes_code_fence():
    answer = "intro paragraph\n\n```python\n" + "x = 1\n" * 50 + "```"
    text, truncated = truncate_answer(answer, limit=80)
    assert truncated and text.startswith("intro paragraph")
    assert text.count("```") % 2 == 0
    assert truncate_answer("short", limit=80) == ("short", False)
