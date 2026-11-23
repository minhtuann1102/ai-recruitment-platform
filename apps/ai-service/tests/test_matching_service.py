"""017 US2 T018: MatchService: embed loi / qua han -> degraded van tra ket qua; log khong chua van ban CV; timing, usage."""
import asyncio
import json
import logging
import time
from datetime import date, datetime, timezone

import pytest

from app.api_error import ApiError
from app.llm.errors import ConfigError, LlmError, LlmTimeoutError
from app.matching.job_index import JobIndexSnapshot, build_mock_snapshot
from app.matching.service import MatchService
from app.matching.settings import load_match_settings
from fakes.fake_match_service import BODY, FakeGateway, StaticIndex, request, run, service

SECRET_HEADLINE = "ZXQ-SECRET-HEADLINE-Backend-Wizard"
SECRET_SUMMARY = "ZXQ-SECRET-SUMMARY-built-quantum-ledger"


def test_embedding_success_is_not_degraded_and_reports_usage_and_timing():
    svc, gw = service()
    res = run(svc)
    meta = res.metadata
    assert (meta.degraded, meta.degraded_reason, meta.mock) == (False, None, False)
    assert meta.usage.embedding_tokens == 37
    assert meta.timing_ms.embed >= 0 and meta.timing_ms.score >= 0
    assert meta.timing_ms.total >= max(meta.timing_ms.embed, meta.timing_ms.score)
    assert res.total == 5 and all(i.components.cosine is not None for i in res.items)
    assert len(gw.texts) == 1


def test_embed_text_has_no_skill_list():
    svc, gw = service()
    run(svc)
    for tech_only in ("Quantum Basket", "Kafka", "Redis", "Docker"):  # chi co trong skills[] / tech[], khong vao van ban
        assert tech_only not in gw.texts[0]
    assert gw.texts[0].startswith("Backend Developer 3 năm kinh nghiệm Java")


@pytest.mark.parametrize("error,reason", [
    (ConfigError("LLM_API_KEY chua dat"), "embedding_unavailable"),
    (LlmTimeoutError("het han"), "embedding_timeout"),
    (LlmError("provider 500"), "embedding_error"),
    (RuntimeError("boom"), "embedding_error"),
])
def test_gateway_error_degrades_with_reason_and_still_returns_results(error, reason):
    svc, _ = service(FakeGateway(error=error))
    res = run(svc)
    meta = res.metadata
    assert meta.degraded is True and meta.degraded_reason == reason and meta.usage.embedding_tokens == 0
    assert (meta.weights.cosine, meta.weights.skill_match, meta.weights.level_fit) == (
        0.0, pytest.approx(0.75), pytest.approx(0.25))  # w2 : w3 chuan hoa lai
    assert res.total == 5 and all(i.components.cosine is None for i in res.items)
    for item in res.items:
        c = item.components
        assert item.score == pytest.approx(0.75 * c.skill_match + 0.25 * c.level_fit, abs=2e-4)


def test_missing_gateway_config_degrades_as_embedding_unavailable():
    def no_gateway():
        raise ConfigError("LLM_API_KEY chua dat")  # get_gateway() khi thieu khoa

    settings = load_match_settings({})
    snap = build_mock_snapshot(datetime(2026, 11, 22, tzinfo=timezone.utc))
    res = asyncio.run(MatchService(settings, StaticIndex(snap), gateway_factory=no_gateway,
                                   today=lambda: date(2026, 11, 22)).recommend(request()))
    assert res.metadata.degraded and res.metadata.degraded_reason == "embedding_unavailable" and res.total == 5


def test_slow_embedding_is_cut_at_the_timeout_and_degrades():
    svc, _ = service(FakeGateway(delay=5.0), env={"MATCH_EMBED_TIMEOUT_S": "0.05"})
    started = time.perf_counter()
    res = run(svc)
    assert time.perf_counter() - started < 1.0
    assert res.metadata.degraded_reason == "embedding_timeout" and res.total == 5
    assert res.metadata.timing_ms.embed >= 40  # do thoi gian da cho


def test_wrong_vector_size_degrades_as_embedding_error():
    svc, _ = service(FakeGateway(dims=8))
    res = run(svc)
    assert res.metadata.degraded_reason == "embedding_error" and res.total == 5


def test_degraded_order_is_stable_and_follows_skill_and_level():
    svc, _ = service(FakeGateway(error=RuntimeError("x")))
    ids = [i.job_id for i in run(svc).items]
    assert ids[0] == "mock:backend-java-mid" and ids == [i.job_id for i in run(svc).items]


def test_logs_contain_counts_and_timings_but_never_cv_text(caplog):
    leaky = RuntimeError(f"provider echoed input: {SECRET_HEADLINE} {SECRET_SUMMARY}")
    cv = json.loads(json.dumps(BODY["cv_profile"]))
    cv["headline"], cv["experiences"][0]["summary"] = SECRET_HEADLINE, SECRET_SUMMARY
    for gateway in (FakeGateway(), FakeGateway(error=leaky)):
        svc, _ = service(gateway)
        with caplog.at_level(logging.DEBUG):
            asyncio.run(svc.recommend(request(cv_profile=cv)))
    assert "match_done" in caplog.text and "match_embedding_degraded" in caplog.text
    for secret in (SECRET_HEADLINE, SECRET_SUMMARY, "Quantum Basket", "Shop API"):
        assert secret not in caplog.text
    done = next(r.getMessage() for r in caplog.records if r.getMessage().startswith("match_done"))
    assert "total=5" in done and "embed_ms=" in done and "score_ms=" in done


def test_mock_mode_uses_hash_embedder_and_never_calls_the_gateway():
    def boom():
        raise AssertionError("mock khong duoc goi gateway")

    settings = load_match_settings({"MATCH_MOCK": "true"})
    snap = build_mock_snapshot(datetime(2026, 11, 22, tzinfo=timezone.utc))
    svc = MatchService(settings, StaticIndex(snap), gateway_factory=boom, today=lambda: date(2026, 11, 22))
    res = asyncio.run(svc.recommend(request()))
    assert res.metadata.mock and not res.metadata.degraded and res.metadata.usage.embedding_tokens == 0
    assert res.total == 5 and all(i.components.cosine is not None for i in res.items)


def test_unknown_track_raises_api_error_422():
    svc, gw = service()
    with pytest.raises(ApiError) as exc:
        run(svc, track="nope")
    assert (exc.value.status_code, exc.value.error) == (422, "unknown_track") and gw.texts == []


def test_as_of_defaults_to_injected_today_and_request_value_wins():
    svc, _ = service(today=date(2031, 1, 1))
    res = asyncio.run(svc.recommend(request(as_of=None)))
    assert res.metadata.as_of == date(2031, 1, 1) and res.total == 0  # het tin mau da het han vao 2031
    assert run(svc).metadata.as_of == date(2026, 11, 21)


def test_empty_index_returns_empty_result_without_calling_the_gateway():
    empty = JobIndexSnapshot(jobs=(), matrix=build_mock_snapshot(datetime.now(timezone.utc)).matrix[:0],
                             embedding_model="text-embedding-3-small",
                             loaded_at=datetime(2026, 11, 22, tzinfo=timezone.utc), source="ai_db")
    svc, gw = service(snapshot=empty)
    res = run(svc)
    assert res.items == [] and res.total == 0 and res.metadata.index_size == 0 and not res.metadata.degraded
    assert gw.texts == []  # khong co JD de cham: khong ton luot embed


def test_page_slice_and_max_results_cap():
    svc, _ = service(env={"MATCH_MAX_RESULTS": "3"})
    res = run(svc, page=1, page_size=2)
    assert res.total == 3 and len(res.items) == 2
    assert [i.job_id for i in run(svc, page=2, page_size=2).items] != [i.job_id for i in res.items]
    assert len(run(svc, page=2, page_size=2).items) == 1 and run(svc, page=3, page_size=2).items == []


@pytest.mark.parametrize("env", [{}, {"MATCH_MOCK": "true"}])
def test_cv_without_any_text_is_degraded_cv_text_empty_without_calling_the_provider(env):
    svc, gw = service(env=env)
    empty = {"schema_version": 1, "headline": " ", "skills": [{"name": "Java", "category": "language",
                                                                 "evidence": "listed"}]}
    res = run(svc, cv_profile=empty)
    meta = res.metadata
    assert meta.degraded and meta.degraded_reason == "cv_text_empty" and gw.texts == []
    assert all(i.components.cosine is None for i in res.items) and res.total == 5  # van tra theo skill + level
    assert meta.weights.cosine == 0.0 and meta.usage.embedding_tokens == 0
