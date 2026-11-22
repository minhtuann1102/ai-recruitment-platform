"""Goi y viec lam tu CV (spec 017 US2): loc cung + cham diem tren snapshot chi muc, embed CV qua LlmGateway.

Khong goi LLM sinh van ban, khong luu vector CV (FR-011). Embed loi / het MATCH_EMBED_TIMEOUT_S / thieu khoa thi van tra
ket qua tu skill_match + level_fit va bat `degraded` kem ly do (FR-014, FR-015). Che do mock dung hash_embedder, khong
cham gateway. Log chi co so luong va thoi gian: khong co van ban CV, ten ky nang, hay noi dung loi cua provider.
"""
import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional, Tuple

import numpy as np

from ..api_error import ApiError
from ..llm.errors import ConfigError, LlmError, LlmTimeoutError
from ..llm.gateway import get_gateway
from ..llm.usage import UsageCollector
from ..models_cv import CvProfile
from .cv_text import build_cv_text, cv_skills
from .hash_embedder import hash_embed
from .job_index import JobIndex, JobIndexSnapshot
from .levels_tracks import TRACK_GROUPS, candidate_level_rank, group_for_track
from .models import MatchComponents, MatchItem, MatchJobsRequest, MatchJobsResponse, MatchMetadata, MatchTiming, MatchUsage
from .scorer import ScoredJob, effective_weights, rank_jobs
from .settings import MatchSettings, load_match_settings

log = logging.getLogger("ai_service.matching")
VN_TZ = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh khong co gio mua he: khong can zoneinfo / tzdata


def _today_vn() -> date:
    return datetime.now(VN_TZ).date()


def _degraded_reason(err: BaseException) -> str:
    if isinstance(err, ConfigError):  # thieu LLM_API_KEY (get_gateway)
        return "embedding_unavailable"
    if isinstance(err, (asyncio.TimeoutError, LlmTimeoutError)):
        return "embedding_timeout"
    return "embedding_error"


def _ms(seconds: float) -> int:
    return int(seconds * 1000)


class MatchService:
    def __init__(self, settings: MatchSettings, index: JobIndex, *, gateway_factory: Callable = get_gateway,
                 today: Callable[[], date] = _today_vn):
        self._settings, self._index = settings, index
        self._gateway_factory, self._today = gateway_factory, today

    async def recommend(self, req: MatchJobsRequest) -> MatchJobsResponse:
        started = time.perf_counter()
        group = group_for_track(req.track)
        if group is None:
            raise ApiError(422, "unknown_track", "track không hợp lệ", {"tracks": sorted(TRACK_GROUPS)})
        snapshot = await self._index.get()  # 503 match_index_unavailable neu lan nap dau loi
        as_of = req.as_of or self._today()
        cv_slugs, unknown = cv_skills(req.cv_profile)
        rank = candidate_level_rank(req.level, req.cv_profile.total_years_experience)

        collector, vector, reason, embed_s = UsageCollector(), None, None, 0.0
        if len(snapshot):  # chi muc rong: khong co JD de cham, khong ton luot embed
            vector, reason, embed_s = await self._embed(req.cv_profile, snapshot, collector)
        scoring = time.perf_counter()
        ranked = rank_jobs(snapshot.jobs, snapshot.matrix, vector, cv_slugs, group=group, as_of=as_of,
                           candidate_rank=rank, weights=self._settings.weights,
                           max_level_gap=self._settings.max_level_gap, max_results=self._settings.max_results,
                           job_ids=req.job_ids)
        score_s = time.perf_counter() - scoring

        start = (req.page - 1) * req.page_size
        meta = MatchMetadata(
            as_of=as_of, weights=effective_weights(self._settings.weights, reason is not None),
            max_level_gap=self._settings.max_level_gap, candidate_level_rank=rank,
            embedding_model=snapshot.embedding_model, index_size=len(snapshot), index_loaded_at=snapshot.loaded_at,
            cv_skill_count=len(cv_slugs), unknown_skills_count=unknown, degraded=reason is not None,
            degraded_reason=reason, mock=self._settings.mock,
            usage=MatchUsage(embedding_tokens=sum(r.input_tokens for r in collector.records if r.agent == "embedding")),
            timing_ms=MatchTiming(embed=_ms(embed_s), score=_ms(score_s), total=_ms(time.perf_counter() - started)))
        log.info("match_done jobs=%d total=%d page=%d page_size=%d cv_skills=%d degraded=%s mock=%s embed_ms=%d "
                 "score_ms=%d total_ms=%d", len(snapshot), len(ranked), req.page, req.page_size, len(cv_slugs),
                 meta.degraded, meta.mock, meta.timing_ms.embed, meta.timing_ms.score, meta.timing_ms.total)
        return MatchJobsResponse(items=[_item(s) for s in ranked[start:start + req.page_size]], page=req.page,
                                 page_size=req.page_size, total=len(ranked), metadata=meta)

    async def _embed(self, cv: CvProfile, snapshot: JobIndexSnapshot,
                     collector: UsageCollector) -> Tuple[Optional[np.ndarray], Optional[str], float]:
        """(vector CV hoac None, ly do degraded hoac None, giay da cho). Loi nao cung thanh degraded, tru huy task."""
        started, text, dims = time.perf_counter(), build_cv_text(cv), snapshot.matrix.shape[1]
        try:
            if self._settings.mock:
                return hash_embed(text, dims), None, time.perf_counter() - started
            gateway = self._gateway_factory()
            vectors = await asyncio.wait_for(gateway.embed([text], collector=collector),
                                             self._settings.embed_timeout_s)
            vector = np.asarray(vectors[0], dtype=np.float64)
            if vector.shape != (dims,):
                raise LlmError("so chieu embedding khong khop chi muc")
            return vector, None, time.perf_counter() - started
        except Exception as err:
            reason = _degraded_reason(err)
            log.warning("match_embedding_degraded reason=%s error=%s", reason, type(err).__name__)
            return None, reason, time.perf_counter() - started


def _item(s: ScoredJob) -> MatchItem:
    return MatchItem(
        job_id=s.job.job_id, title=s.job.title, group=s.job.group, level=s.job.level, deadline=s.job.deadline,
        score=s.score, components=MatchComponents(cosine=s.cosine, skill_match=s.skill_match, level_fit=s.level_fit),
        matched_skills=list(s.matched_skills), missing_skills=list(s.missing_skills), notes=list(s.notes))


_service: Optional[MatchService] = None


def get_match_service() -> MatchService:
    """Service dung chung theo env. Cau hinh sai (MATCH_WEIGHTS...) -> ConfigError; goi luc khoi dong (main.lifespan)
    de service tu choi khoi dong thay vi loi o request dau. Khong cham DB o day."""
    global _service
    if _service is None:
        settings = load_match_settings()
        _service = MatchService(settings, JobIndex(settings))
    return _service
