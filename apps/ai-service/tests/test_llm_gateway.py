import asyncio
import logging

import pytest
from pydantic import BaseModel

from app.llm.errors import LlmOutputError
from app.llm.gateway import LlmGateway, build_client
from app.llm.settings import load_llm_settings
from app.llm.usage import UsageCollector
from fakes.fake_llm import FakeOpenAI, embedding_reply, reply, status_error, timeout_error

MSGS = [{"role": "user", "content": "noi dung bi mat"}]


class Out(BaseModel):
    answer: str


def make(script, **env):
    llm = load_llm_settings({"LLM_API_KEY": "k", **env})
    sleeps = []

    async def fake_sleep(d):
        sleeps.append(d)

    client = FakeOpenAI(script)
    return LlmGateway(llm, client, env={}, sleep=fake_sleep, rng=lambda: 0.0), client, sleeps


def run(coro):
    return asyncio.run(coro)


def test_structured_success_uses_strict_schema_and_agent_params():
    gw, client, _ = make([reply('{"answer": "ok"}')])
    res = run(gw.complete("evaluator", MSGS, Out, prompt_version="v3"))
    assert res.data == Out(answer="ok") and res.record.prompt_version == "v3"
    call = client.calls[0]
    assert call["response_format"]["type"] == "json_schema" and call["response_format"]["json_schema"]["strict"]
    assert (call["temperature"], call["max_tokens"], call["seed"]) == (0.0, 400, 7)
    assert res.record.input_tokens == 10 and res.record.output_tokens == 5 and res.record.attempts == 1


def test_json_object_fallback_when_structured_outputs_disabled():
    gw, client, _ = make([reply('{"answer": "ok"}')], LLM_STRUCTURED_OUTPUTS="false")
    run(gw.complete("planner", MSGS, Out))
    assert client.calls[0]["response_format"] == {"type": "json_object"}


def test_plain_text_when_no_schema():
    gw, client, _ = make([reply("xin chao")])
    res = run(gw.complete("interviewer", MSGS))
    assert res.data == "xin chao" and "response_format" not in client.calls[0]


def test_retries_transient_errors_then_succeeds():
    gw, client, sleeps = make([timeout_error(), status_error(429), reply('{"answer": "ok"}')])
    res = run(gw.complete("planner", MSGS, Out))
    assert res.record.attempts == 3 and len(client.calls) == 3 and sleeps == [0.5, 1.5]


def test_client_error_is_not_retried():
    gw, client, _ = make([status_error(401)])
    with pytest.raises(Exception):
        run(gw.complete("planner", MSGS, Out))
    assert len(client.calls) == 1


def test_invalid_json_gets_one_repair_with_temperature_zero():
    gw, client, _ = make([reply("khong phai json"), reply('{"answer": "da sua"}')])
    res = run(gw.complete("planner", MSGS, Out))
    assert res.data.answer == "da sua" and res.record.repaired is True
    repair_call = client.calls[1]
    assert repair_call["temperature"] == 0
    assert "Output trước không hợp lệ" in repair_call["messages"][-1]["content"]
    assert res.record.input_tokens == 20  # tinh ca lan repair


def test_second_invalid_output_raises_without_leaking_content():
    gw, client, _ = make([reply("loi 1"), reply("loi 2 bi mat")])
    with pytest.raises(LlmOutputError) as exc:
        run(gw.complete("planner", MSGS, Out))
    assert len(client.calls) == 2 and "bi mat" not in str(exc.value)


def test_length_retries_once_with_1_5x_max_tokens():
    gw, client, _ = make([reply('{"answer": "cut', finish_reason="length"), reply('{"answer": "ok"}')])
    res = run(gw.complete("evaluator", MSGS, Out))
    assert res.data.answer == "ok"
    assert [c["max_tokens"] for c in client.calls] == [400, 600]


def test_length_twice_raises():
    gw, client, _ = make([reply("x", finish_reason="length"), reply("y", finish_reason="length")])
    with pytest.raises(LlmOutputError):
        run(gw.complete("evaluator", MSGS, Out))
    assert len(client.calls) == 2


def test_usage_collector_receives_metadata_without_content():
    gw, _, _ = make([reply('{"answer": "ok"}'), reply('{"answer": "ok"}')])
    col = UsageCollector()
    run(gw.complete("evaluator", MSGS, Out, prompt_version="v1", collector=col))
    run(gw.complete("evaluator", MSGS, Out, prompt_version="v1", collector=col))
    meta = col.to_metadata()
    assert meta["usage"]["evaluator"] == {"input_tokens": 20, "output_tokens": 10}
    assert meta["prompt_versions"] == {"evaluator": "v1"} and meta["fallbacks"] == []
    assert "bi mat" not in str(meta)


def test_logs_have_no_content_by_default_and_content_only_when_enabled(caplog):
    gw, _, _ = make([reply('{"answer": "cau tra loi rieng tu"}')])
    with caplog.at_level(logging.DEBUG, logger="ai_service.llm"):
        run(gw.complete("planner", MSGS, Out))
    assert "llm_call agent=planner" in caplog.text
    assert "bi mat" not in caplog.text and "rieng tu" not in caplog.text
    caplog.clear()
    gw2, _, _ = make([reply('{"answer": "cau tra loi rieng tu"}')], LOG_LLM_IO="true")
    with caplog.at_level(logging.DEBUG, logger="ai_service.llm"):
        run(gw2.complete("planner", MSGS, Out))
    assert "rieng tu" in caplog.text


def test_embed_checks_dimensions_and_retries():
    good = [[0.1] * 1536, [0.2] * 1536]
    gw, client, sleeps = make([status_error(500), embedding_reply(good)])
    col = UsageCollector()
    assert run(gw.embed(["a", "b"], collector=col)) == good
    assert sleeps == [0.5] and col.records[0].agent == "embedding" and col.records[0].input_tokens == 7
    gw_bad, _, _ = make([embedding_reply([[0.1] * 10])])
    with pytest.raises(LlmOutputError):
        run(gw_bad.embed(["a"]))


def test_sdk_client_has_its_own_retries_disabled():
    client = build_client(load_llm_settings({"LLM_API_KEY": "k"}))
    assert client.max_retries == 0
