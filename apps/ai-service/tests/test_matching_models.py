"""017 US2 T024: request / response pydantic dung contract match-jobs-api.md."""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.matching.models import (MatchComponents, MatchItem, MatchJobsRequest, MatchJobsResponse, MatchMetadata,
                                 MatchTiming, MatchUsage)
from app.matching.settings import MatchWeights

CV = {"headline": "Backend Developer"}


def req(**kw):
    return MatchJobsRequest.model_validate({"cv_profile": CV, "track": "java_backend", **kw})


def test_minimal_request_defaults():
    r = req()
    assert (r.page, r.page_size, r.level, r.as_of, r.job_ids) == (1, 10, None, None, None)
    assert r.cv_profile.headline == "Backend Developer"


def test_track_is_a_plain_string_so_unknown_track_reaches_the_router():
    assert req(track="not_a_track").track == "not_a_track"  # router tra 422 unknown_track, khong phai invalid_request


@pytest.mark.parametrize("level", ["fresher", "junior", "middle", "senior"])
def test_level_values(level):
    assert req(level=level).level == level


@pytest.mark.parametrize("bad", [{"level": "lead"}, {"level": "Mid"}, {"page": 0}, {"page_size": 0},
                                 {"page_size": 51}, {"job_ids": []}, {"job_ids": ["x"] * 201}, {"job_ids": [""]}])
def test_invalid_values_rejected(bad):
    with pytest.raises(ValidationError):
        req(**bad)


def test_page_size_and_job_ids_boundaries_accepted():
    assert req(page_size=50, job_ids=["x"] * 200).page_size == 50 and req(page_size=1).page_size == 1


def test_missing_required_fields_rejected():
    with pytest.raises(ValidationError):
        MatchJobsRequest.model_validate({"cv_profile": CV})
    with pytest.raises(ValidationError):
        MatchJobsRequest.model_validate({"track": "java_backend"})


def test_as_of_accepts_only_yyyy_mm_dd():
    assert req(as_of="2026-11-21").as_of == date(2026, 11, 21)
    for bad in ("21/11/2026", "2026-11-31", "2026-11-21T00:00:00", "20261121", 20261121, "", "hôm nay"):
        with pytest.raises(ValidationError):
            req(as_of=bad)


def make_meta(**kw):
    base = dict(
        as_of=date(2026, 11, 21), weights=MatchWeights(0.6, 0.3, 0.1), max_level_gap=1, candidate_level_rank=2,
        embedding_model="text-embedding-3-small", index_size=360,
        index_loaded_at=datetime(2026, 11, 21, 16, 2, 11, tzinfo=timezone.utc), cv_skill_count=9,
        unknown_skills_count=2, degraded=False, degraded_reason=None, mock=False,
        usage=MatchUsage(embedding_tokens=212), timing_ms=MatchTiming(embed=180, score=4, total=190))
    base.update(kw)
    return MatchMetadata(**base)


def test_response_json_shape_matches_contract():
    item = MatchItem(job_id="careerlink:1", title="Backend Developer (Java)", group="backend", level="Mid",
                     deadline=date(2026, 12, 1), score=0.712,
                     components=MatchComponents(cosine=0.583, skill_match=0.857, level_fit=1.0),
                     matched_skills=["Java"], missing_skills=["Kafka"], notes=[])
    body = MatchJobsResponse(items=[item], page=1, page_size=10, total=37, metadata=make_meta()).model_dump(mode="json")
    assert set(body) == {"items", "page", "page_size", "total", "metadata"}
    assert body["items"][0] == {
        "job_id": "careerlink:1", "title": "Backend Developer (Java)", "group": "backend", "level": "Mid",
        "deadline": "2026-12-01", "score": 0.712,
        "components": {"cosine": 0.583, "skill_match": 0.857, "level_fit": 1.0},
        "matched_skills": ["Java"], "missing_skills": ["Kafka"], "notes": []}
    m = body["metadata"]
    assert set(m) == {"as_of", "weights", "max_level_gap", "candidate_level_rank", "embedding_model", "index_size",
                      "index_loaded_at", "cv_skill_count", "unknown_skills_count", "degraded", "degraded_reason",
                      "mock", "usage", "timing_ms"}
    assert m["as_of"] == "2026-11-21" and m["index_loaded_at"] == "2026-11-21T16:02:11Z"
    assert m["weights"] == {"cosine": 0.6, "skill_match": 0.3, "level_fit": 0.1}
    assert m["usage"] == {"embedding_tokens": 212} and m["timing_ms"] == {"embed": 180, "score": 4, "total": 190}


def test_degraded_item_and_nullable_fields():
    item = MatchItem(job_id="x", title="t", group="backend", level=None, deadline=None, score=0.5,
                     components=MatchComponents(cosine=None, skill_match=0.5, level_fit=0.5))
    body = item.model_dump(mode="json")
    assert body["components"]["cosine"] is None and body["level"] is None and body["deadline"] is None
    assert body["matched_skills"] == body["missing_skills"] == body["notes"] == []


def test_degraded_reason_values():
    for reason in ("embedding_unavailable", "embedding_timeout", "embedding_error"):
        assert make_meta(degraded=True, degraded_reason=reason).degraded_reason == reason
    with pytest.raises(ValidationError):
        make_meta(degraded_reason="boom")
