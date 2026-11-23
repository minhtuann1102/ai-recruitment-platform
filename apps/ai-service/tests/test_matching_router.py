"""017 US2 T016: POST /api/match/jobs o che do mock (MATCH_MOCK=true): token, loi dau vao, tat dinh, loc cung, phan trang."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm.errors import ConfigError
from app.main import app
from app.matching import service as match_service

URL = "/api/match/jobs"
BODY = json.loads((Path(__file__).parent / "fixtures" / "matching" / "cv-java-middle.json").read_text(encoding="utf-8"))
# Chi muc mau (mock_jobs.json) tai as_of 2026-11-21, track java_backend (nhom backend), ung vien bac 2 (middle),
# max_level_gap 1: loai Intern (lech 2) va tin da dong (het han); con 5 tin
BACKEND_PASSING = {"mock:backend-java-mid", "mock:backend-java-junior", "mock:backend-node-senior",
                   "mock:backend-python-mid", "mock:backend-java-no-level"}


@pytest.fixture()
def match_client(monkeypatch):
    monkeypatch.setenv("MATCH_MOCK", "true")
    monkeypatch.delenv("AI_SERVICE_INTERNAL_TOKEN", raising=False)
    monkeypatch.setattr(match_service, "_service", None)  # tao lai service theo env cua test; monkeypatch tra ve sau
    return TestClient(app)


def call(client, **override):
    return client.post(URL, json={**BODY, **override})


def stable(body: dict) -> dict:
    """Bo phan do thoi gian chay (timing_ms) de so sanh hai lan goi."""
    meta = {k: v for k, v in body["metadata"].items() if k != "timing_ms"}
    return {**body, "metadata": meta}


def test_missing_or_wrong_token_is_401(match_client, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_INTERNAL_TOKEN", "s3cret-token")
    r = match_client.post(URL, json=BODY)
    assert r.status_code == 401 and r.json()["error"] == "unauthorized"
    assert match_client.post(URL, json=BODY, headers={"X-Internal-Token": "wrong"}).status_code == 401
    assert match_client.post(URL, json=BODY, headers={"X-Internal-Token": "s3cret-token"}).status_code == 200


def test_unknown_track_is_422_unknown_track(match_client):
    for track in ("not_a_track", "mobile_fullstack", "../etc"):
        r = call(match_client, track=track)
        assert r.status_code == 422 and r.json()["error"] == "unknown_track", track


@pytest.mark.parametrize("bad", [{"page_size": 51}, {"page_size": 0}, {"page": 0}, {"level": "lead"},
                                 {"as_of": "21/11/2026"}, {"job_ids": ["x"] * 201}, {"job_ids": []},
                                 {"job_ids": ["x" * 65]}])
def test_invalid_input_is_422_invalid_request(match_client, bad):
    r = call(match_client, **bad)
    assert r.status_code == 422 and r.json()["error"] == "invalid_request"


def test_missing_cv_profile_or_track_is_invalid_request(match_client):
    for field in ("cv_profile", "track"):
        r = match_client.post(URL, json={k: v for k, v in BODY.items() if k != field})
        assert r.status_code == 422 and r.json()["error"] == "invalid_request"


def test_two_identical_calls_give_identical_results_and_mock_flag(match_client):
    a, b = call(match_client), call(match_client)
    assert a.status_code == b.status_code == 200
    assert stable(a.json()) == stable(b.json())
    meta = a.json()["metadata"]
    assert meta["mock"] is True and meta["degraded"] is False and meta["degraded_reason"] is None
    assert meta["usage"] == {"embedding_tokens": 0} and meta["embedding_model"].startswith("mock")
    assert set(meta["timing_ms"]) == {"embed", "score", "total"}


def test_metadata_describes_the_query(match_client):
    meta = call(match_client).json()["metadata"]
    assert meta["as_of"] == "2026-11-21" and meta["weights"] == {"cosine": 0.6, "skill_match": 0.3, "level_fit": 0.1}
    assert meta["max_level_gap"] == 1 and meta["candidate_level_rank"] == 2 and meta["index_size"] == 14
    assert meta["cv_skill_count"] == 6  # java, spring-boot, postgresql, docker, kafka, redis; Quantum Basket la la
    assert meta["unknown_skills_count"] == 1 and meta["index_loaded_at"].endswith("Z")


def test_level_defaults_from_years_and_as_of_defaults_to_today(match_client):
    body = {k: v for k, v in BODY.items() if k not in ("level", "as_of")}
    r = match_client.post(URL, json=body)
    assert r.status_code == 200 and r.json()["metadata"]["candidate_level_rank"] == 2  # 3 nam -> Mid
    assert len(r.json()["metadata"]["as_of"]) == 10
    r = match_client.post(URL, json={**body, "level": "fresher"})
    assert r.json()["metadata"]["candidate_level_rank"] == 1


def test_items_satisfy_hard_filter_and_formula(match_client):
    body = call(match_client).json()
    assert {i["job_id"] for i in body["items"]} == BACKEND_PASSING and body["total"] == 5
    for item in body["items"]:
        assert item["group"] == "backend" and item["deadline"] >= "2026-11-21"
        assert item["level"] in ("Junior", "Mid", "Senior", None)  # lech toi da 1 bac so voi middle
        c = item["components"]
        assert c["cosine"] is not None and 0 <= c["cosine"] <= 1
        assert item["score"] == pytest.approx(0.6 * c["cosine"] + 0.3 * c["skill_match"] + 0.1 * c["level_fit"],
                                              abs=3e-4)
    scores = [i["score"] for i in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_matched_and_missing_skills_agree_with_skill_match(match_client):
    for item in call(match_client).json()["items"]:
        matched, missing = item["matched_skills"], item["missing_skills"]
        if matched or missing:
            assert item["components"]["skill_match"] == pytest.approx(len(matched) / (len(matched) + len(missing)),
                                                                      abs=1e-4)
            assert not set(matched) & set(missing)
        else:
            assert item["components"]["skill_match"] == 0 and "jd_no_skills" in item["notes"]
    top = {i["job_id"]: i for i in call(match_client).json()["items"]}["mock:backend-java-mid"]
    assert top["matched_skills"] == ["Java", "Kafka", "PostgreSQL", "Spring Boot"] and top["missing_skills"] == []
    assert top["components"]["skill_match"] == 1.0 and top["components"]["level_fit"] == 1.0


def test_java_jobs_rank_above_unrelated_node_job(match_client):
    ids = [i["job_id"] for i in call(match_client).json()["items"]]
    assert ids[0] == "mock:backend-java-mid" and ids.index("mock:backend-java-junior") < ids.index(
        "mock:backend-node-senior")


def test_no_level_job_carries_note_and_half_level_fit(match_client):
    item = next(i for i in call(match_client).json()["items"] if i["job_id"] == "mock:backend-java-no-level")
    assert item["level"] is None and item["components"]["level_fit"] == 0.5 and "jd_no_level" in item["notes"]


def test_page_past_total_is_empty_items_not_an_error(match_client):
    r = call(match_client, page=9)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == [] and body["total"] == 5 and body["page"] == 9 and body["page_size"] == 10


def test_pagination_slices_the_same_ranked_list(match_client):
    full = [i["job_id"] for i in call(match_client).json()["items"]]
    pages = [call(match_client, page=p, page_size=2).json() for p in (1, 2, 3)]
    assert [len(p["items"]) for p in pages] == [2, 2, 1] and all(p["total"] == 5 for p in pages)
    assert [i["job_id"] for p in pages for i in p["items"]] == full


def test_job_ids_restricts_to_the_given_set_and_still_applies_filters(match_client):
    ids = ["mock:backend-java-mid", "mock:frontend-react-junior", "mock:backend-java-expired", "mock:unknown-id"]
    body = call(match_client, job_ids=ids).json()
    assert [i["job_id"] for i in body["items"]] == ["mock:backend-java-mid"] and body["total"] == 1


def test_other_tracks_use_their_own_group(match_client):
    body = call(match_client, track="devops_engineer", level="senior").json()
    assert {i["group"] for i in body["items"]} == {"devops"}
    assert body["metadata"]["candidate_level_rank"] == 3
    skill_less = [i for i in body["items"] if i["job_id"] == "mock:devops-manager"]  # Manager lech 2 bac: bi loc
    assert skill_less == []
    body = call(match_client, track="frontend_react", level="junior").json()
    assert [i["job_id"] for i in body["items"]][0] == "mock:frontend-react-junior"


def test_no_job_passes_gives_empty_list_without_error(match_client):
    body = call(match_client, as_of="2031-01-01").json()  # moi tin mau het han truoc 2031
    assert body["items"] == [] and body["total"] == 0 and body["metadata"]["index_size"] == 14


def test_bad_weights_stop_the_service_from_starting(monkeypatch):
    monkeypatch.setenv("MATCH_WEIGHTS", "0.9,0.9,0.9")
    monkeypatch.setattr(match_service, "_service", None)
    with pytest.raises(ConfigError, match="MATCH_WEIGHTS"):
        with TestClient(app):  # lifespan: get_match_service() doc cau hinh, khong cham DB
            pass


def test_real_mode_without_ai_db_url_is_503_match_index_unavailable(monkeypatch):
    monkeypatch.setenv("MATCH_MOCK", "false")
    monkeypatch.delenv("AI_DB_URL", raising=False)
    monkeypatch.delenv("AI_SERVICE_INTERNAL_TOKEN", raising=False)
    monkeypatch.setattr(match_service, "_service", None)
    r = TestClient(app).post(URL, json=BODY)
    assert r.status_code == 503 and r.json()["error"] == "match_index_unavailable"
