"""Probe tool + strict JSON: dung transport gia (khong goi mang) de kiem hinh dang request va cach doc ket qua."""
import asyncio
import json

from scripts.probe_tool_strict_json import probe, render, request


def tool_reply(n=1, cached=None):
    calls = [{"id": f"c{i}", "type": "function", "function": {"name": "lookup_reference",
                                                              "arguments": '{"query": "x"}'}} for i in range(n)]
    return 200, {"provider": "OpenAI", "choices": [{"message": {"content": None, "tool_calls": calls}}],
                 "usage": {"prompt_tokens_details": {"cached_tokens": cached}}}


def content_reply(content):
    return 200, {"provider": "OpenAI", "choices": [{"message": {"content": content}}], "usage": {}}


def test_request_shape_is_strict_and_non_parallel():
    body = request("m", "hi")
    assert body["tools"][0]["function"]["strict"] is True and body["parallel_tool_calls"] is False
    assert body["provider"] == {"require_parameters": True} and body["response_format"]["json_schema"]["strict"]
    assert "provider" not in request("m", "hi", require_parameters=None)
    assert "response_format" not in request("m", "hi", fmt=None)


def test_probe_reads_seven_answers_from_fake_transport():
    seen = []

    async def post(body):
        seen.append(body)
        if body["tool_choice"] == "none" and body["response_format"]["json_schema"]["name"] == "short":
            return content_reply(json.dumps({"text": "x" * 60}))  # maxLength bi bo qua
        if body["tool_choice"] == "none":
            return content_reply(json.dumps({"score": 6, "reason": "ok"}))
        return tool_reply(n=2, cached=1024)  # model van goi 2 tool dù parallel=false

    rows = asyncio.run(probe(post, "m"))
    assert [r["n"] for r in rows] == [1, 2, 3, 4, 5, 6, 7]
    by = {r["n"]: r for r in rows}
    assert by[1]["ok"] and by[2]["ok"] and by[5]["ok"] and by[7]["ok"] is None
    assert by[3]["ok"] is False and "len=60" in by[3]["detail"]  # vuot 20: bo qua maxLength
    assert by[6]["ok"] is False  # 2 tool call du parallel=false
    assert any(b["provider"] == {"require_parameters": False} for b in seen if "provider" in b)
    assert "| 1 |" in render("m", "http://x", rows) and "sk-" not in render("m", "http://x", rows)


def test_probe_records_http_errors_and_network_failures_without_raising():
    async def post(body):
        if body["tool_choice"] == "none":
            raise TimeoutError("boom")
        return 404, {"error": {"message": "No endpoints found that support the requested parameters"}}

    rows = asyncio.run(probe(post, "m"))
    assert all(r["ok"] in (False, None) for r in rows)
    assert "HTTP 404" in rows[0]["detail"] and "HTTP 0" in rows[1]["detail"]
