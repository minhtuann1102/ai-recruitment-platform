"""Fake dung chung cho test MatchService (017): chi muc tinh, gateway embed gia, request / service helper."""
import asyncio
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.llm.usage import CallRecord
from app.matching.hash_embedder import EMBEDDING_DIMS, hash_embed
from app.matching.job_snapshot import build_mock_snapshot
from app.matching.models import MatchJobsRequest
from app.matching.service import MatchService
from app.matching.settings import load_match_settings

BODY = json.loads((Path(__file__).parents[1] / "fixtures" / "matching" / "cv-java-middle.json").read_text(
    encoding="utf-8"))


class StaticIndex:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def get(self):
        return self.snapshot


class FakeGateway:
    """embed gia: tra vector, hoac nem loi, hoac cho lau; ghi lai van ban da nhan."""

    def __init__(self, error=None, delay=0.0, tokens=37, dims=EMBEDDING_DIMS):
        self.error, self.delay, self.tokens, self.dims, self.texts = error, delay, tokens, dims, []

    async def embed(self, texts, *, collector=None):
        self.texts.extend(texts)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        if collector is not None:
            collector.add(CallRecord("embedding", "text-embedding-3-small", input_tokens=self.tokens))
        return [hash_embed(t, self.dims).tolist() for t in texts]


def request(**override):
    return MatchJobsRequest.model_validate({**BODY, **override})


def service(gateway=None, env=None, snapshot=None, today=date(2026, 11, 22)):
    settings = load_match_settings({"MATCH_EMBED_TIMEOUT_S": "0.3", **(env or {})})
    if snapshot is None:
        snapshot = build_mock_snapshot(datetime(2026, 11, 22, 8, 0, 0, tzinfo=timezone.utc))
    gw = gateway or FakeGateway()
    return MatchService(settings, StaticIndex(snapshot), gateway_factory=lambda: gw, today=lambda: today), gw


def run(svc, **override):
    return asyncio.run(svc.recommend(request(**override)))
