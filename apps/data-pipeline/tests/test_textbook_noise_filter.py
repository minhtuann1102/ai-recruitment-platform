"""T018: loc nhieu tu dong (research R7) — moi ly do mot vi du bi bat, doan tot duoc giu."""
import pytest

from pipeline.textbook_noise_filter import noise_reason, prose_word_count

PROSE = (
    "The write-ahead log records every change before it is applied to the data files, so after a crash the "
    "server can replay the log and restore a consistent state without losing any committed transaction."
)


def test_blocked_heading_case_insensitive():
    for heading in ("See Also", "SEE ALSO", "see also", "What’s Next", "Further Reading:"):
        assert noise_reason(["Intro", heading], PROSE) == "blocked_heading"
    assert noise_reason(["See Also", "Details"], PROSE) is None  # chi tieu de cuoi moi bi chan
    assert noise_reason([], PROSE) is None


def test_code_only_over_70_percent():
    body = "Example:\n\n```python\n" + "\n".join(f"value_{i} = compute({i}) + offset" for i in range(15)) + "\n```"
    assert noise_reason(["Usage"], body) == "code_only"


def test_link_list_of_link_only_and_short_items():
    body = "\n".join([
        "- [Getting started with the replication guide](https://example.com/a)",
        "- https://example.com/b",
        "- Backup guide",
        "* Restore guide",
        "1. [Monitoring](https://example.com/c)",
        "Related pages:",
    ])
    assert noise_reason(["Resources"], body) == "link_list"


def test_too_short_counts_words_outside_code():
    assert noise_reason(["Tip"], "Use EXPLAIN to inspect a plan.") == "too_short"
    assert noise_reason(["Tip"], "") == "too_short"
    body = "Short intro here.\n\n```sql\n" + "SELECT * FROM orders WHERE id = 1;\n" * 3 + "```"
    assert noise_reason(["Tip"], body) in ("too_short", "code_only")
    assert prose_word_count(body) == 3


def test_explanation_with_short_code_block_is_kept():
    body = f"{PROSE}\n\n```sql\nCHECKPOINT;\n```\n\nThe command forces an immediate checkpoint of all dirty buffers."
    assert noise_reason(["WAL", "Checkpoints"], body) is None


def test_bullets_that_are_full_sentences_are_kept():
    body = "\n".join([
        "- Each transaction writes its changes to the log before touching the table files on disk.",
        "- The checkpointer flushes dirty buffers at intervals so recovery has less log to replay.",
        "- Archiving copies finished segments elsewhere, which enables point-in-time recovery of the cluster.",
        "- Replicas stream the same log records and apply them in order to stay close to the primary.",
    ])
    assert noise_reason(["WAL", "Overview"], body) is None


@pytest.mark.parametrize("heading", ["Replication", "Next Steps Review"])
def test_normal_heading_not_blocked(heading):
    assert noise_reason([heading], PROSE) is None
