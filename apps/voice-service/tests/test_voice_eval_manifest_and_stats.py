"""Bo do voice (spec 015 T026/T027): manifest co dinh dung quy tac R10, thong ke thuan (khong mang)."""
import json
from collections import Counter

import pytest

from evals.build_manifest import MANIFEST, build, load_golden, reading_sheet
from evals.eval_inputs import load_pricing
from evals.eval_stats import latency_table, percentile, recognition_summary, session_credit, stt_credit


@pytest.fixture(scope="module")
def golden():
    return load_golden()


def test_manifest_follows_r10_rules(golden):
    clips = build(golden)
    read = [c for c in clips if c["kind"] == "read"]
    free = [c for c in clips if c["kind"] == "free"]
    assert len(read) == 24 and len(free) == 6
    by_id = {r["id"]: r for r in golden}
    assert len({c["golden_id"] for c in read}) == 24  # moi golden doc mot lan
    assert not any(by_id[c["golden_id"]].get("adversarial") for c in read)
    tiers = Counter((c["track"], by_id[c["golden_id"]]["intended_tier"]) for c in read)
    assert set(tiers.values()) == {2} and len({t for t, _ in tiers}) == 4
    per_speaker = Counter((c["track"], c["speaker"]) for c in read)
    assert set(per_speaker.values()) == {3}
    assert all("golden_id" not in c for c in free) and Counter(c["speaker"] for c in free) == {"s1": 3, "s2": 3}


def test_committed_manifest_matches_builder(golden):
    with MANIFEST.open(encoding="utf-8") as f:
        assert [json.loads(line) for line in f if line.strip()] == build(golden)


def test_reading_sheet_only_lists_own_clips(golden):
    clips = build(golden)
    sheet = reading_sheet(clips, golden, "s1")
    by_id = {r["id"]: r for r in golden}
    for c in clips:
        assert (f"## {c['clip_id']} " in sheet) == (c["speaker"] == "s1")
        if c["kind"] == "read" and c["speaker"] == "s1":
            assert by_id[c["golden_id"]]["answer"] in sheet


def test_build_fails_when_a_tier_is_short(golden):
    with pytest.raises(ValueError, match="java_backend/strong"):
        build([r for r in golden if not (r["track"] == "java_backend" and r.get("intended_tier") == "strong")])


def test_percentile_is_nearest_rank():
    assert percentile([], 95) is None
    assert percentile([3.0, 1.0, 2.0], 50) == 2.0
    assert percentile([float(i) for i in range(1, 21)], 95) == 19.0
    assert percentile([1.0, 9.0], 95) == 9.0


def test_latency_table_buckets_and_targets():
    rows = {r["bucket"]: r for r in latency_table([(12.0, 7.0), (29.9, 9.0), (45.0, 21.0), (120.0, 30.0), (None, 1.0)])}
    assert rows["≤ 30 s"]["n"] == 2 and rows["≤ 30 s"]["passed"] is True
    assert rows["30–90 s"]["p95"] == 21.0 and rows["30–90 s"]["passed"] is False
    assert rows["> 90 s"]["n"] == 1 and rows["> 90 s"]["passed"] is None


def test_recognition_summary_pools_terms_and_handles_empty():
    s = recognition_summary([{"ser": 0.1, "terms_found": 3, "terms_total": 4},
                             {"ser": 0.3, "terms_found": 0, "terms_total": 0}])
    assert s["clips"] == 2 and s["ser_mean"] == pytest.approx(0.2) and s["term_rate"] == 0.75
    assert recognition_summary([])["term_rate"] is None


def test_credit_from_committed_pricing():
    pricing = load_pricing()
    assert stt_credit(60, pricing) == pytest.approx(2.2)
    session = session_credit(pricing)
    assert session["stt"] == pytest.approx(17.6) and session["tts"] == pytest.approx(29.6)
