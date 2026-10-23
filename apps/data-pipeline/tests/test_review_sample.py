import csv
import json

from pipeline.review_sample_command import sample_pairs, write_review_files


def pair(i):
    return {
        "qa_id": f"cr-devi-node-{i:08x}",
        "topic_id": "node.core.event-loop",
        "difficulty": "easy",
        "question": f"Câu {i}?",
        "answer": "Đáp án tiếng Việt đủ dài để đọc.",
        "question_original": f"Question {i}?",
        "answer_original": "Original answer text.",
        "source_lang": "en",
    }


def test_sample_is_stable_and_csv_has_no_content(tmp_path):
    enriched = tmp_path / "enriched"
    enriched.mkdir()
    (enriched / "devi-node.json").write_text(json.dumps([pair(i) for i in range(30)]), encoding="utf-8")
    first = sample_pairs(enriched, per_source=5, seed=1, skip=set())
    assert first == sample_pairs(enriched, per_source=5, seed=1, skip=set())
    review, sheet = tmp_path / "reviews" / "review.csv", tmp_path / "sheet.txt"
    assert write_review_files(first, review, sheet) == 5

    rows = list(csv.DictReader(review.open(encoding="utf-8", newline="")))
    assert len(rows) == 5 and set(rows[0]) == {"cid", "source", "topic_id", "difficulty", "verdict", "reviewer", "note"}
    assert all(r["verdict"] == "" for r in rows)
    assert "Question" in sheet.read_text(encoding="utf-8") and "Câu" in sheet.read_text(encoding="utf-8")

    reviewed = {r["cid"] for r in rows}
    again = sample_pairs(enriched, per_source=5, seed=1, skip=reviewed)
    assert not reviewed & {p["qa_id"] for p in again["devi-node"]}
