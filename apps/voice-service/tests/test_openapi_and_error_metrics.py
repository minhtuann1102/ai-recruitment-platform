"""Swagger khop hanh vi (khong quang cao 422, co body loi theo contract) va loi 500 ngoai du kien duoc dem trong /metrics."""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import FakeBlaze, make_settings

ERROR_REFS = ("400", "401", "503")


@pytest.fixture()
def schema():
    with TestClient(create_app(make_settings(), transport=FakeBlaze({}).transport)) as client:
        return client.get("/openapi.json").json()


def responses(schema, path):
    return schema["paths"][path]["post"]["responses"]


def test_no_endpoint_advertises_422_and_validation_schemas_are_gone(schema):
    for path in ("/api/voice/transcribe", "/api/voice/speak", "/api/voice/session-summary"):
        assert "422" not in responses(schema, path), path
    assert "HTTPValidationError" not in schema.get("components", {}).get("schemas", {})


def test_transcribe_documents_every_contract_error_with_the_error_body(schema):
    documented = responses(schema, "/api/voice/transcribe")
    assert {"200", "400", "401", "402", "411", "413", "415", "429", "502", "503", "504"} <= set(documented)
    assert "consent_required" in documented["400"]["description"]
    assert documented["411"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorBody")
    assert "multipart/form-data" in schema["paths"]["/api/voice/transcribe"]["post"]["requestBody"]["content"]


def test_speak_and_summary_document_their_errors(schema):
    speak, summary = responses(schema, "/api/voice/speak"), responses(schema, "/api/voice/session-summary")
    assert {"200", "400", "401", "402", "429", "502", "503", "504"} <= set(speak)
    assert "audio/mpeg" in speak["200"]["content"] and "text_too_long" in speak["400"]["description"]
    assert set(ERROR_REFS) <= set(summary) and "200" in summary


def test_unexpected_500_is_counted_in_metrics_and_has_the_error_format(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("noi dung nhay cam khong duoc ra log hay response")
    monkeypatch.setattr("app.summary_route.summarize", boom)
    app = create_app(make_settings(), transport=FakeBlaze({}).transport)
    with TestClient(app, raise_server_exceptions=False) as client:
        before = client.get("/metrics").text
        r = client.post("/api/voice/session-summary", json={"turns": []})
        after = client.get("/metrics").text
    assert r.status_code == 500 and r.json()["error"] == "internal_error" and "nhay cam" not in r.text
    pattern = r'voice_requests_total\{endpoint="/api/voice/session-summary",error="internal_error",status="error"\} (\d+)'
    count = lambda text: int(next(iter(re.findall(pattern, text)), "0"))  # noqa: E731
    assert count(after) == count(before) + 1
