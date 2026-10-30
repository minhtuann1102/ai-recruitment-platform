"""Tracing Langfuse: dung SDK that, xuat span ra bo nho (khong can khoa, khong goi mang)."""
import asyncio
import gc
import json
import time
import uuid

import pytest
from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from conftest import parse_sse
from fakes.fake_llm import FakeOpenAI, FakeStream, embedding_reply, reply, status_error
from pydantic import BaseModel

from test_interview_flow import play, strong

from app import tracing
from app.cv_text import redact_pii
from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from app.main import _TurnStream, app

MSGS = [{"role": "user", "content": "Em ten A, email a.b@gmail.com, so 0912345678"}]
CTX = {"track": "java_backend", "level": "junior"}
INPUT, OUTPUT = "langfuse.observation.input", "langfuse.observation.output"


class Out(BaseModel):
    answer: str


@pytest.fixture()
def finished(monkeypatch):
    monkeypatch.delenv("LANGFUSE_TRACING_ENABLED")
    exporter = InMemorySpanExporter()
    client = Langfuse(public_key=f"pk-{uuid.uuid4()}", secret_key="sk", base_url="http://localhost:9", flush_at=1,
                      span_exporter=exporter, tracer_provider=TracerProvider(), mask=tracing.mask_pii,
                      environment="test")
    monkeypatch.setattr(tracing, "_client", client)
    monkeypatch.setattr(tracing, "_loaded", True)

    def spans():
        client.flush()
        return {s.name: s for s in exporter.get_finished_spans()}

    yield spans
    client.shutdown()


def gateway(script, dims=None):
    env = {"LLM_API_KEY": "k", **({"EMBEDDING_DIMENSIONS": str(dims)} if dims else {})}
    return LlmGateway(load_llm_settings(env), FakeOpenAI(script), env={}, rng=lambda: 0.0)


def in_request(coro_fn):
    """Chay nhu mot request: mo trace, goi, dong trace."""
    async def main():
        tracing.start_request("next_turn", session_id="sess-t", turn_number=2, tags=["java_backend"])
        try:
            return await coro_fn()
        finally:
            tracing.finish_request("ok", "-")
    return asyncio.run(main())


def test_generation_has_model_usage_output_session_and_masked_input(finished):
    gw = gateway([reply('{"answer": "ok"}')])
    in_request(lambda: gw.complete("evaluator", MSGS, Out, prompt_version="v4"))
    spans = finished()
    gen, root = spans["evaluator"], spans["next_turn"]
    a = gen.attributes
    assert gen.parent.span_id == root.context.span_id and gen.context.trace_id == root.context.trace_id
    assert a["session.id"] == "sess-t" and a["langfuse.trace.name"] == "next_turn"
    assert a["langfuse.observation.type"] == "generation" and a["langfuse.version"] == "v4"
    assert a["langfuse.observation.model.name"] == "openai/gpt-4o-mini"
    assert json.loads(a["langfuse.observation.usage_details"]) == {"input": 10, "output": 5}
    assert json.loads(a[OUTPUT]) == {"answer": "ok"}
    assert "[EMAIL]" in a[INPUT] and "[PHONE]" in a[INPUT]
    assert "gmail" not in a[INPUT] and "0912345678" not in a[INPUT] and "Em ten A" in a[INPUT]


def test_failed_llm_call_is_marked_error_and_still_raises(finished):
    gw = gateway([status_error(400)])
    with pytest.raises(Exception):
        in_request(lambda: gw.complete("planner", MSGS, Out))
    a = finished()["planner"].attributes
    assert a["langfuse.observation.level"] == "ERROR" and a["langfuse.observation.status_message"] == "BadRequestError"


def collect(gw):
    async def run():
        return [t async for t in gw.stream("interviewer", MSGS, prompt_version="v3")]
    return run


def test_stream_records_ttft_and_joined_output(finished):
    assert in_request(collect(gateway([FakeStream(["Vậy khi ", "A gọi B"])]))) == ["Vậy khi ", "A gọi B"]
    a = finished()["interviewer"].attributes
    assert a[OUTPUT] == "Vậy khi A gọi B" and "langfuse.observation.completion_start_time" in a


def test_broken_stream_keeps_received_part_and_error_level(finished):
    with pytest.raises(Exception):
        in_request(collect(gateway([FakeStream(["Vậy khi ", "A gọi B"], fail_after=1)])))
    a = finished()["interviewer"].attributes
    assert a[OUTPUT] == "Vậy khi " and a["langfuse.observation.level"] == "ERROR"


def test_consumer_leaving_stream_early_still_ends_generation(finished):
    gw = gateway([FakeStream(["Vậy khi ", "A gọi B"])])

    async def leave():
        stream = gw.stream("interviewer", MSGS)
        await stream.__anext__()
        await stream.aclose()

    in_request(leave)
    assert finished()["interviewer"].attributes[OUTPUT] == "Vậy khi "


def test_embedding_keeps_input_and_no_vectors(finished):
    gw = gateway([embedding_reply([[0.1, 0.2]])], dims=2)
    in_request(lambda: gw.embed(["hashmap là gì"]))
    a = finished()["embedding"].attributes
    assert a["langfuse.observation.type"] == "embedding" and json.loads(a[OUTPUT]) == {"vectors": 1}


def test_nested_span_is_parent_of_llm_calls_and_siblings_stay_separate(finished):
    gw = gateway([reply("ok"), reply("ok")])

    async def work():
        async def one():
            with tracing.observation("rag_turn", "retriever", nest=True):
                await gw.complete("evaluator", MSGS)

        await asyncio.gather(one(), gw.complete("planner", MSGS))

    in_request(work)
    spans = finished()
    assert spans["evaluator"].parent.span_id == spans["rag_turn"].context.span_id
    assert spans["planner"].parent.span_id == spans["next_turn"].context.span_id


def test_llm_call_outside_a_request_creates_no_trace(finished):
    asyncio.run(gateway([reply("ok")]).complete("planner", MSGS))
    assert finished() == {}


def test_routes_produce_session_trace_with_answer_and_next_question(client, finished, capsys):
    done = parse_sse(client.post("/api/start", json={"session_id": "sess-r", **CTX}).text)[-1][1]
    body = {"session_id": "sess-r", "level": "junior", "track": "java_backend", "plan": done["plan"],
            "state": done["state"], "turn_number": 1, "question": done["question"],
            "turn_kind": done["turn"]["turn_kind"], "answer": "Em dùng HashMap", "elapsed_seconds": 60}
    next_done = parse_sse(client.post("/api/next-turn", json=body).text)[-1][1]
    spans = finished()
    root = spans["next_turn"].attributes
    assert spans["start"].attributes["session.id"] == root["session.id"] == "sess-r"
    assert root["langfuse.trace.tags"] == ("java_backend", "junior")
    assert json.loads(root[INPUT])["answer"] == "Em dùng HashMap" and root[OUTPUT] == next_done["question"]
    assert json.loads(root["langfuse.observation.metadata.status"]) == "ok"
    assert spans["rag_turn"].parent.span_id == spans["next_turn"].context.span_id
    trace_id = format(spans["next_turn"].context.trace_id, "032x")
    assert f"trace={trace_id}" in capsys.readouterr().err  # tu dong log tim ra trace


def test_route_error_ends_trace_with_error_level(client, finished):
    done = parse_sse(client.post("/api/start", json={"session_id": "sess-x", **CTX}).text)[-1][1]
    body = {"session_id": "sess-x", "level": "junior", "track": "java_backend", "plan": done["plan"],
            "state": {**done["state"], "phase": "done"}, "turn_number": 1, "question": "q", "answer": "a",
            "elapsed_seconds": 60}
    assert client.post("/api/next-turn", json=body).status_code == 409
    a = finished()["next_turn"].attributes
    assert a["langfuse.observation.level"] == "ERROR" and a["langfuse.observation.status_message"] == "ApiError"


def asgi_post(path, body):
    """Goi app truc tiep; client ngat ngay sau khi nhan chunk thu 2 (uvicorn: receive tra http.disconnect)."""
    bodies, sent, gone = [json.dumps(body).encode()], [], asyncio.Event()

    async def receive():
        if bodies:
            return {"type": "http.request", "body": bodies.pop(), "more_body": False}
        await gone.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)
        if len(sent) >= 2:
            gone.set()
            await asyncio.sleep(0)

    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1",
             "method": "POST", "path": path, "raw_path": path.encode(), "query_string": b"",
             "headers": [(b"content-type", b"application/json")], "client": ("t", 1), "server": ("t", 80),
             "scheme": "http", "root_path": ""}
    asyncio.run(app(scope, receive, send))
    return sent


def test_client_disconnect_ends_trace_as_cancelled_in_its_own_context(finished, capsys):
    sent = asgi_post("/api/start", {"session_id": "sess-d", **CTX})
    assert sent[0]["type"] == "http.response.start"
    gc.collect()  # generator da dong, GC khong con dong no trong context khac
    a = finished()["start"].attributes
    assert a["langfuse.observation.level"] == "WARNING" and a["langfuse.observation.status_message"] == "-"
    line = next(x for x in map(json.loads, (e for e in capsys.readouterr().err.splitlines() if e.startswith("{")))
                if x["event"] == "request_done")
    assert line["session_id"] == "sess-d" and "status=cancelled" in line["msg"]


def test_stream_never_started_still_finishes_request(finished):
    closed = []

    async def body():
        yield "x"

    async def main():
        async def receive():
            return {"type": "http.disconnect"}

        async def send(_):
            raise OSError("client gone")

        await _TurnStream(body(), lambda: closed.append(True))({}, receive, send)

    with pytest.raises(BaseException):
        asyncio.run(main())
    assert closed == [True]


def test_timeout_on_llm_call_is_not_shown_as_success(finished):
    class Hang:
        def __init__(self):
            self.chat = self
            self.completions = self

        async def create(self, **_):
            await asyncio.sleep(3)

    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), Hang(), env={})

    async def call():
        await asyncio.wait_for(gw.complete("planner", MSGS), 0.01)

    with pytest.raises(asyncio.TimeoutError):
        in_request(call)
    assert finished()["planner"].attributes["langfuse.observation.level"] == "WARNING"


def test_cv_jd_and_finalize_routes_open_their_own_trace(client, finished):
    r = client.post("/api/jd/parse", json={"track": "java_backend", "jd_text": "Backend Java Spring " * 20})
    assert r.status_code == 200
    plan, state, turns, _ = play(client, "junior", strong)
    r = client.post("/api/finalize", json={"session_id": "sess-f", "track": "java_backend", "level": "junior",
                                           "plan": plan, "state": state, "end_reason": "plan_complete",
                                           "duration_s": 1500, "turns": turns})
    assert r.status_code == 200
    spans = finished()
    assert "session.id" not in spans["jd_parse"].attributes
    assert spans["finalize"].attributes["session.id"] == "sess-f"
    assert json.loads(spans["finalize"].attributes[OUTPUT])["score"] == r.json()["overall"]["score"]


@pytest.mark.parametrize("broken", ["start_observation", "update", "end"])
def test_sdk_failure_never_breaks_the_request(client, monkeypatch, broken):
    class Obs:
        trace_id = "t"

        def __getattr__(self, name):
            def call(**_):
                if name == broken:
                    raise RuntimeError("langfuse down")
                return self
            return call

    monkeypatch.setattr(tracing, "_client", Obs())
    monkeypatch.setattr(tracing, "_loaded", True)
    r = client.post("/api/start", json={"session_id": "s", **CTX})
    assert r.status_code == 200 and parse_sse(r.text)[-1][0] == "done"
    assert tracing._root.get() is tracing._OFF


def test_disabled_without_keys_or_when_flag_is_false(monkeypatch):
    monkeypatch.setattr(tracing, "_client", None)
    monkeypatch.setattr(tracing, "_loaded", False)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")
    assert tracing._get_client() is None
    monkeypatch.setattr(tracing, "_loaded", False)
    monkeypatch.delenv("LANGFUSE_TRACING_ENABLED")
    monkeypatch.delenv("LANGFUSE_SECRET_KEY")
    assert tracing._get_client() is None


def test_mask_walks_nested_values_and_keeps_other_types():
    out = tracing.mask_pii(data={"a": ["x@y.vn", {"b": 0.5}], "n": 3})
    assert out == {"a": ["[EMAIL]", {"b": 0.5}], "n": 3}


def test_mask_stays_fast_on_a_long_unbroken_string():
    started = time.perf_counter()
    assert redact_pii("a" * 100_000 + " x@y.vn").endswith("[EMAIL]")
    assert time.perf_counter() - started < 0.2  # regex email tung la O(n^2): 15 s voi 100k ky tu
