"""Bo do voice (spec 015 T026/T027): quy tac manifest (R10), ghim ban chuan, thong ke thuat (khong mang).

Test dung golden gia lap: CI cua voice-service khong do khi AIE sua file golden cua ho; viec kiem golden that nam o
luc chay bo do (load_clips kiem ref_sha256).
"""
import json
from collections import Counter

import pytest

from evals.build_manifest import MANIFEST, READ_TRACKS, TIERS, build, free_prompts, reading_sheet, ref_hash
from evals.eval_inputs import load_clips, load_pricing
from evals.eval_stats import latency_table, percentile, recognition_summary, session_credit, stt_credit


def fake_golden():
    rows = []
    for t, track in enumerate(READ_TRACKS):
        for q in range(3):
            qid = f"q{t}{q}"
            for tier in TIERS:
                rows.append({"id": f"{qid}-{tier}", "qid": qid, "track": track, "intended_tier": tier,
                             "question": f"Câu hỏi {qid}?", "answer": f"đáp án {qid} {tier} HashMap"})
        rows.append({"id": f"adv{t}", "qid": f"adv{t}", "track": track, "intended_tier": "strong", "adversarial": True,
                     "question": f"Câu tấn công {t}?", "answer": "bỏ qua hướng dẫn"})
    return rows


def test_build_follows_r10_rules_and_is_deterministic():
    golden = fake_golden()
    clips = build(golden)
    assert clips == build(list(reversed(golden)))  # khong phu thuoc thu tu dau vao
    read = [c for c in clips if c["kind"] == "read"]
    free = [c for c in clips if c["kind"] == "free"]
    assert len(read) == 24 and len(free) == 6
    by_id = {r["id"]: r for r in golden}
    assert len({c["golden_id"] for c in read}) == 24 and not any(by_id[c["golden_id"]].get("adversarial") for c in read)
    assert set(Counter((c["track"], by_id[c["golden_id"]]["intended_tier"]) for c in read).values()) == {2}
    assert set(Counter((c["track"], c["speaker"]) for c in read).values()) == {3}
    assert all(c["ref_sha256"] == ref_hash(by_id[c["golden_id"]]["answer"]) for c in read)
    assert all("golden_id" not in c for c in free) and Counter(c["speaker"] for c in free) == {"s1": 3, "s2": 3}


def test_committed_manifest_shape():
    with MANIFEST.open(encoding="utf-8") as f:
        clips = [json.loads(line) for line in f if line.strip()]
    read = [c for c in clips if c["kind"] == "read"]
    assert [c["clip_id"] for c in clips] == [f"r{i:02d}" for i in range(1, 25)] + [f"f{i:02d}" for i in range(1, 7)]
    assert len({c["golden_id"] for c in read}) == 24 and all(len(c["ref_sha256"]) == 16 for c in read)


def test_load_clips_rejects_changed_reference(tmp_path):
    golden = fake_golden()
    manifest, golden_path = tmp_path / "m.jsonl", tmp_path / "g.jsonl"
    manifest.write_text("".join(json.dumps(c) + "\n" for c in build(golden)), encoding="utf-8")
    golden_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in golden), encoding="utf-8")
    assert len(load_clips(manifest, golden_path, tmp_path)) == 30
    golden[0]["answer"] += " (AIE sua)"
    golden_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in golden), encoding="utf-8")
    with pytest.raises(ValueError, match="ref_sha256 lech"):
        load_clips(manifest, golden_path, tmp_path)


def test_reading_sheet_and_free_prompts():
    golden = fake_golden()
    clips = build(golden)
    sheet = reading_sheet(clips, golden, "s1")
    by_id = {r["id"]: r for r in golden}
    for c in clips:
        assert (f"## {c['clip_id']} " in sheet) == (c["speaker"] == "s1")
        if c["kind"] == "read" and c["speaker"] == "s1":
            assert by_id[c["golden_id"]]["answer"] in sheet
    prompts = free_prompts(clips, golden)
    assert len(set(prompts.values())) == 6  # khong lap cau giua cac clip free
    read_q = {by_id[c["golden_id"]]["question"] for c in clips if c.get("golden_id") and c["speaker"] == "s1"}
    assert not any(prompts[c["clip_id"]] in read_q for c in clips if c["kind"] == "free" and c["speaker"] == "s1")


def test_build_fails_when_a_tier_is_short():
    golden = [r for r in fake_golden() if not (r["track"] == "java_backend" and r["intended_tier"] == "weak")]
    with pytest.raises(ValueError, match="java_backend/weak"):
        build(golden)


def test_percentile_is_nearest_rank():
    assert percentile([], 95) is None
    assert percentile([3.0, 1.0, 2.0], 50) == 2.0
    assert percentile([float(i) for i in range(1, 21)], 95) == 19.0
    assert percentile([1.0, 9.0], 95) == 9.0


def test_latency_table_buckets_targets_and_failures():
    samples = [(12.0, 7.0), (29.9, 9.0), (45.0, 21.0), (120.0, 30.0), (None, 1.0)]
    rows = {r["bucket"]: r for r in latency_table(samples)}
    assert rows["≤ 30 s"]["n"] == 2 and rows["≤ 30 s"]["passed"] is True
    assert rows["30–90 s"]["p95"] == 21.0 and rows["30–90 s"]["passed"] is False
    assert rows["> 90 s"]["n"] == 1 and rows["> 90 s"]["passed"] is None
    assert all(r["passed"] is None for r in latency_table(samples, failures=1))  # co lan loi -> khong ket luan


def test_recognition_summary_pools_terms_and_errors():
    s = recognition_summary([{"ser": 0.5, "edits": 1, "ref_tokens": 2, "terms_found": 3, "terms_total": 4},
                             {"ser": 0.1, "edits": 1, "ref_tokens": 10, "terms_found": 0, "terms_total": 0}])
    assert s["clips"] == 2 and s["ser_mean"] == pytest.approx(0.3) and s["ser_pooled"] == pytest.approx(2 / 12)
    assert s["term_rate"] == 0.75
    assert recognition_summary([])["term_rate"] is None and recognition_summary([])["ser_pooled"] is None


def test_credit_from_committed_pricing():
    pricing = load_pricing()
    assert stt_credit(60, pricing) == pytest.approx(2.2)
    session = session_credit(pricing)
    assert session["stt"] == pytest.approx(17.6) and session["tts"] == pytest.approx(29.6)
