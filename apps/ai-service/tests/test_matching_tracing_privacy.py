"""017 US2 review M3: van ban CV khong bao gio roi khoi service qua trace Langfuse.

LlmGateway.embed ghi observation "embedding" kem input=[van ban CV]. An toan vi route goi y khong mo trace (khong
tracing.start_request) nen observation do la no-op. Test ghi lai moi observation / Langfuse client: route ma mo trace thi
test do.
"""
import contextvars
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import tracing
from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from app.main import app
from app.matching import service as match_service
from app.matching.hash_embedder import EMBEDDING_DIMS
from app.matching.job_snapshot import build_mock_snapshot
from app.matching.service import MatchService
from app.matching.settings import load_match_settings
from fakes.fake_llm import FakeOpenAI, embedding_reply
from fakes.fake_match_service import BODY, StaticIndex

SECRET = "ZXQ-SECRET-HEADLINE-quantum-ledger"


class RecordingObservation:
    def __init__(self, client):
        self.client = client

    def start_observation(self, **fields):
        self.client.observations.append(fields)
        return RecordingObservation(self.client)

    def update(self, **fields):
        self.client.observations.append(fields)

    def end(self):
        pass


class RecordingClient:
    """Thay Langfuse: ghi moi observation duoc mo."""

    def __init__(self):
        self.observations = []

    def start_observation(self, **fields):
        self.observations.append(fields)
        return RecordingObservation(self)


@pytest.fixture()
def recorder(monkeypatch):
    client = RecordingClient()
    monkeypatch.setattr(tracing, "_get_client", lambda: client)
    return client


def test_the_recorder_sees_a_real_trace(recorder):
    # doi chung: neu ai mo trace thi recorder phai thay, nen "khong thay gi" o test duoi la co nghia
    # copy_context: start_request dat contextvar cua trace; khong de ro ri sang test khac (TestClient chep context)
    contextvars.copy_context().run(tracing.start_request, "control", input="CONTROL-INPUT")
    assert any(o.get("input") == "CONTROL-INPUT" for o in recorder.observations)


def test_match_endpoint_opens_no_trace_and_the_cv_text_never_reaches_an_observation(recorder, monkeypatch):
    fake_openai = FakeOpenAI([embedding_reply([[0.01] * EMBEDDING_DIMS])])
    gateway = LlmGateway(load_llm_settings({"LLM_API_KEY": "test-key"}), client=fake_openai)
    settings = load_match_settings({})
    snapshot = build_mock_snapshot(datetime(2026, 11, 22, tzinfo=timezone.utc))
    service = MatchService(settings, StaticIndex(snapshot), gateway_factory=lambda: gateway)
    monkeypatch.setattr(match_service, "_service", service)
    monkeypatch.delenv("AI_SERVICE_INTERNAL_TOKEN", raising=False)

    # moi lan gateway ghi observation: ghi lai cha cua no co that khong (obs None = no-op)
    parents = []
    original_child = tracing.Observation.child

    def spy_child(self, name, as_type, fields):
        parents.append((name, self._obs is not None, json.dumps(fields, default=str)))
        return original_child(self, name, as_type, fields)

    monkeypatch.setattr(tracing.Observation, "child", spy_child)

    cv = json.loads(json.dumps(BODY["cv_profile"]))
    cv["headline"] = SECRET
    r = TestClient(app).post("/api/match/jobs", json={**BODY, "cv_profile": cv})

    assert r.status_code == 200 and r.json()["metadata"]["degraded"] is False  # that su da embed qua gateway
    assert SECRET in json.dumps(fake_openai.calls[0]["input"])  # provider nhan van ban CV
    assert recorder.observations == []  # khong trace nao duoc mo
    assert parents and all(name == "embedding" and not real for name, real, _ in parents)  # observation no-op
    assert SECRET not in json.dumps(recorder.observations, default=str)
