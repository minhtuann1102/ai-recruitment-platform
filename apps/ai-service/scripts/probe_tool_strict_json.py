"""Probe 7 cau hoi live: tools(strict) + JSON schema strict qua OpenRouter, model Evaluator (plan agentic phase 01).

Chay: python -m scripts.probe_tool_strict_json [--out ../../plans/reports/probe-<ngay>-tool-strict-json.md]
(tu thu muc apps/ai-service). Doc LLM_API_KEY / LLM_BASE_URL / model Evaluator qua load_llm_settings; KHONG in khoa.
Moi probe chi gui vai request nho. Ket qua la bang Markdown de dan vao report; loi 4xx/5xx duoc ghi lai, khong nem.
"""
import argparse
import asyncio
import json
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx

Post = Callable[[Dict[str, Any]], Awaitable[Tuple[int, Dict[str, Any]]]]

TOOL = {"type": "function", "function": {
    "name": "lookup_reference", "description": "Tra cuu tai lieu tham chieu cua kho theo cau truy van ngan.",
    "strict": True, "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                                   "required": ["query"], "additionalProperties": False}}}
VERDICT = {"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": {
    "type": "object", "properties": {"score": {"type": "integer"}, "reason": {"type": "string"}},
    "required": ["score", "reason"], "additionalProperties": False}}}
SHORT = {"type": "json_schema", "json_schema": {"name": "short", "strict": True, "schema": {
    "type": "object", "properties": {"text": {"type": "string", "maxLength": 20}},
    "required": ["text"], "additionalProperties": False}}}
PAD = "Quy tac cham diem: " + "Dung tai lieu tham chieu khi can, khong bia nguon. " * 120  # > 1024 token cho cache


def request(model: str, user: str, *, tool_choice: Any = "auto", fmt: Optional[Dict] = VERDICT,
            require_parameters: Optional[bool] = True, parallel: bool = False) -> Dict[str, Any]:
    body: Dict[str, Any] = {"model": model, "temperature": 0, "max_tokens": 200, "tools": [TOOL],
                            "tool_choice": tool_choice, "parallel_tool_calls": parallel,
                            "messages": [{"role": "system", "content": PAD}, {"role": "user", "content": user}]}
    if fmt:
        body["response_format"] = fmt
    if require_parameters is not None:
        body["provider"] = {"require_parameters": require_parameters}
    return body


def message(resp: Dict[str, Any]) -> Dict[str, Any]:
    return ((resp.get("choices") or [{}])[0]).get("message") or {}


def brief(status: int, resp: Dict[str, Any]) -> str:
    if status != 200:
        return f"HTTP {status}: {json.dumps(resp.get('error', resp), ensure_ascii=False)[:300]}"
    calls, content = message(resp).get("tool_calls") or [], message(resp).get("content")
    return f"HTTP 200 provider={resp.get('provider')} tool_calls={len(calls)} content_null={content is None}"


async def probe(post: Post, model: str) -> List[Dict[str, Any]]:
    """-> [{n, question, ok (True/False/None = can doi chieu tay), detail}] theo thu tu 7 cau hoi cua research."""
    ask_tool = "Hay goi lookup_reference de tra cuu 'HashMap resize' truoc khi tra loi."
    out: List[Dict[str, Any]] = []

    async def send(body):
        try:
            return await post(body)
        except Exception as err:  # mang / timeout: ghi lai, khong dung ca probe
            return 0, {"error": f"{type(err).__name__}"}

    s1, r1 = await send(request(model, ask_tool, tool_choice="auto"))
    out.append({"n": 1, "question": "tools(strict) + response_format json_schema + require_parameters=true cung 1 request, "
                "tra tool_calls (content null)?",
                "ok": s1 == 200 and bool(message(r1).get("tool_calls")), "detail": brief(s1, r1)})
    s2, r2 = await send(request(model, "Cham: 'HashMap dung bucket'. Tra score 0-10 va reason.", tool_choice="none"))
    valid = False
    if s2 == 200:
        try:
            parsed = json.loads(message(r2).get("content") or "")
            valid = isinstance(parsed.get("score"), int) and isinstance(parsed.get("reason"), str)
        except (ValueError, AttributeError):
            pass
    out.append({"n": 2, "question": "tool_choice=none + json_schema: content hop le schema?", "ok": valid,
                "detail": brief(s2, r2)})
    s3, r3 = await send(request(model, "Viet mot cau dai hon 80 ky tu ve HashMap.", tool_choice="none", fmt=SHORT))
    text = ""
    if s3 == 200:
        try:
            text = json.loads(message(r3).get("content") or "{}").get("text", "")
        except ValueError:
            pass
    out.append({"n": 3, "question": "maxLength trong strict schema: bi tu choi (400) hay bo qua / ep?",
                "ok": s3 == 200 and 0 < len(text) <= 20,
                "detail": f"{brief(s3, r3)} len={len(text)} (200 + len > 20 = bo qua; 400 = tu choi; <= 20 = ep)"})
    s4, r4 = await send(request(model, ask_tool, require_parameters=False))
    out.append({"n": 4, "question": "provider thuc te + require_parameters=false co khac require_parameters=true?",
                "ok": s1 == 200 or s4 == 200,
                "detail": f"true: {brief(s1, r1)} | false: {brief(s4, r4)}"})
    s5, r5 = await send(request(model, ask_tool))
    cached = ((r5.get("usage") or {}).get("prompt_tokens_details") or {}).get("cached_tokens")
    out.append({"n": 5, "question": "cached_tokens > 0 o lan goi thu 2 (co tools)?",
                "ok": bool(cached), "detail": f"{brief(s5, r5)} cached_tokens={cached}"})
    s6, r6 = await send(request(model, "Hay tra cuu CA HAI: 'HashMap resize' va 'ConcurrentHashMap' bang 2 lan goi."))
    n_calls = len(message(r6).get("tool_calls") or [])
    out.append({"n": 6, "question": "parallel_tool_calls=false: moi luot <= 1 tool call?", "ok": s6 == 200 and n_calls <= 1,
                "detail": f"{brief(s6, r6)} tool_calls={n_calls}"})
    out.append({"n": 7, "question": "docs OpenRouter / OpenAI: muc ket hop tools + schema, danh sach keyword?",
                "ok": None, "detail": "doc lai tay (khong probe duoc); ghi ket luan vao report"})
    return out


def render(model: str, base_url: str, rows: List[Dict[str, Any]]) -> str:
    lines = [f"# Probe tools(strict) + JSON schema ({model})", f"base_url: {base_url}", "",
             "| # | Cau hoi | Ket qua | Chi tiet |", "|---|---|---|---|"]
    for r in rows:
        mark = {True: "OK", False: "KHONG", None: "tay"}[r["ok"]]
        lines.append(f"| {r['n']} | {r['question']} | {mark} | {r['detail']} |")
    return "\n".join(lines) + "\n"


async def main_async(out_path: Optional[str]) -> int:
    from app.llm.errors import ConfigError
    from app.llm.settings import agent_settings, load_llm_settings

    try:
        llm = load_llm_settings()
    except ConfigError as err:
        print(f"LOI CAU HINH: {err}")
        return 2
    model = agent_settings("evaluator", llm).model
    headers = {"Authorization": f"Bearer {llm.api_key}"}  # khong in ra o bat ky dau

    async with httpx.AsyncClient(base_url=llm.base_url, headers=headers, timeout=30.0) as client:
        async def post(body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
            resp = await client.post("/chat/completions", json=body)
            try:
                return resp.status_code, resp.json()
            except ValueError:
                return resp.status_code, {"error": resp.text[:300]}

        text = render(model, llm.base_url, await probe(post, model))
    print(text)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="ghi bang Markdown vao file nay")
    return asyncio.run(main_async(parser.parse_args().out))


if __name__ == "__main__":
    sys.exit(main())
