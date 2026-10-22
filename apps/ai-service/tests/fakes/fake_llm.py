"""LLM gia theo kich ban, CHI de kiem logic dieu phoi (retry, repair, fallback), khong khang dinh chat luong cham."""
from types import SimpleNamespace
from typing import Any, Dict, List

import httpx
import openai

_REQ = httpx.Request("POST", "http://fake/v1/chat/completions")


def reply(content: str, finish_reason: str = "stop", prompt_tokens: int = 10, completion_tokens: int = 5):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


def embedding_reply(vectors: List[List[float]], prompt_tokens: int = 7):
    return SimpleNamespace(data=[SimpleNamespace(embedding=v) for v in vectors],
                           usage=SimpleNamespace(prompt_tokens=prompt_tokens))


def status_error(status: int, headers: Dict[str, str] = None) -> openai.APIStatusError:
    cls = {400: openai.BadRequestError, 401: openai.AuthenticationError, 403: openai.PermissionDeniedError,
           429: openai.RateLimitError}.get(status, openai.InternalServerError)
    resp = httpx.Response(status, request=_REQ, headers=headers or {})
    return cls(f"fake {status}", response=resp, body=None)


def timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(request=_REQ)


class _Endpoint:
    def __init__(self, owner: "FakeOpenAI", kind: str):
        self._owner, self._kind = owner, kind

    async def create(self, **kwargs: Any):
        self._owner.calls.append({"kind": self._kind, **kwargs})
        if not self._owner.script:
            raise AssertionError("het kich ban cua FakeOpenAI")
        item = self._owner.script.pop(0)
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

    def __init__(self, parts: List[str], fail_after: int = None, delay: float = 0.0):
        self.parts, self.fail_after, self.delay = parts, fail_after, delay

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
        yield SimpleNamespace(choices=[], usage=SimpleNamespace(prompt_tokens=20, completion_tokens=len(self.parts)))
