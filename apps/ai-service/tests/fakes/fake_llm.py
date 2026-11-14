"""LLM gia theo kich ban, CHI de kiem logic dieu phoi (retry, repair, fallback), khong khang dinh chat luong cham."""
import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import httpx
import openai

_REQ = httpx.Request("POST", "http://fake/v1/chat/completions")


def usage_with_cache(prompt_tokens: int, completion_tokens: int, cached_tokens: int):
    return SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                           prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens))


def reply(content: str, finish_reason: str = "stop", prompt_tokens: int = 10, completion_tokens: int = 5,
          usage=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)],
        usage=usage or SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


def tool_reply(calls, prompt_tokens: int = 10, completion_tokens: int = 5):
    """Luot model doi goi cong cu: content=None, finish_reason=tool_calls. calls: [(id, ten, chuoi JSON doi so)]."""
    tool_calls = [SimpleNamespace(id=cid, type="function", function=SimpleNamespace(name=name, arguments=args))
                  for cid, name, args in calls]
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=tool_calls),
                                 finish_reason="tool_calls")],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


def embedding_reply(vectors: List[List[float]], prompt_tokens: int = 7):
    return SimpleNamespace(data=[SimpleNamespace(embedding=v) for v in vectors],
                           usage=SimpleNamespace(prompt_tokens=prompt_tokens))


def status_error(status: int, headers: Dict[str, str] = None, message: str = None) -> openai.APIStatusError:
    cls = {400: openai.BadRequestError, 401: openai.AuthenticationError, 403: openai.PermissionDeniedError,
           404: openai.NotFoundError,
           429: openai.RateLimitError}.get(status, openai.InternalServerError)
    resp = httpx.Response(status, request=_REQ, headers=headers or {})
    return cls(message or f"fake {status}", response=resp, body=None)


def timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(request=_REQ)


class Slow:
    """Phan tu kich ban tra ve sau `delay` giay: provider giu ket noi, httpx cua client gia khong het han."""

    def __init__(self, delay: float, item: Any):
        self.delay, self.item = delay, item


def limit_agent(monkeypatch, agent: str, timeout_s: float, budget_s: float = None) -> None:
    """Ha timeout cua agent de test khong phai cho that."""
    from app.llm import settings
    temperature, max_tokens, _, seed, _ = settings._DEFAULTS[agent]
    monkeypatch.setitem(settings._DEFAULTS, agent, (temperature, max_tokens, timeout_s, seed, budget_s))


class _Endpoint:
    def __init__(self, owner: "FakeOpenAI", kind: str):
        self._owner, self._kind = owner, kind

    async def create(self, **kwargs: Any):
        self._owner.calls.append({"kind": self._kind, **kwargs})
        if not self._owner.script:
            raise AssertionError("het kich ban cua FakeOpenAI")
        item = self._owner.script.pop(0)
        if isinstance(item, Slow):
            await asyncio.sleep(item.delay)
            item = item.item
        if isinstance(item, BaseException):
            raise item
        return item


class FakeOpenAI:
    """script: danh sach phan tu theo thu tu moi lan goi; la Exception thi nem, nguoc lai tra ve."""

    def __init__(self, script: List[Any]):
        self.script, self.calls = list(script), []
        self.chat = SimpleNamespace(completions=_Endpoint(self, "chat"))
        self.embeddings = _Endpoint(self, "embedding")


class FakeStream:
    """Stream gia: tra lan luot cac manh text, chunk cuoi co usage; fail_after=n thi nem loi sau n manh."""

    def __init__(self, parts: List[str], fail_after: int = None, delay: float = 0.0, usage=None):
        self.parts, self.fail_after, self.delay, self.usage = parts, fail_after, delay, usage

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        import asyncio
        for i, part in enumerate(self.parts):
            if self.fail_after is not None and i >= self.fail_after:
                raise timeout_error()
            if self.delay:
                await asyncio.sleep(self.delay)
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=part))], usage=None)
        yield SimpleNamespace(choices=[], usage=self.usage or SimpleNamespace(prompt_tokens=20,
                                                                              completion_tokens=len(self.parts)))
