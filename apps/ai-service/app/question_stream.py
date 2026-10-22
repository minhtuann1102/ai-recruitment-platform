"""Stream cau hoi cua Interviewer thanh event SSE kem fallback va kiem bang code (FR-AI-037..039, 071).

- Loi truoc token dau (hoac qua FIRST_TOKEN_TIMEOUT_S): gui cau du phong qua event `token`.
- Loi giua stream: gui `replace` chua cau du phong day du.
- Stream xong ma cau vi pham (rong, qua dai, lo diem, lap cau da hoi - Jaccard >= 0.8): `replace` bang cau du phong.
Moi lan dung cau du phong ghi `interviewer_fallback` vao metadata.fallbacks.
"""
import asyncio
import logging
import re
from typing import AsyncIterator, List, Optional, Tuple

from .agents.interviewer import QuestionSpec, fallback_question
from .llm.usage import CallRecord, UsageCollector
from .mock_evaluator import fold
from .sse import chunk_tokens

log = logging.getLogger("ai_service.interviewer")
FIRST_TOKEN_TIMEOUT_S = 5.0
MAX_WORDS = 120  # prompt yeu cau <= 80; de du phong cho cau dan
REPEAT_JACCARD = 0.8
_LEAK = re.compile(r"\d+([.,]\d+)?\s*/\s*10\b|\bband\s*\d|diem (cua ban|so)|dap an (la|dung)")
_MARKDOWN = re.compile(r"[*_#`>]+")


def _words(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", fold(text)))


def jaccard(a: str, b: str) -> float:
    x, y = _words(a), _words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def is_repeat(question: str, asked: List[str]) -> bool:
    return any(jaccard(question, q) >= REPEAT_JACCARD for q in asked)


def clean_question(text: str) -> str:
    """Van ban thuan cho TTS: bo ky hieu markdown, gop khoang trang."""
    return " ".join(_MARKDOWN.sub("", text).split())


def violation(question: str, asked: List[str]) -> Optional[str]:
    if not question:
        return "empty"
    if len(question.split()) > MAX_WORDS:
        return "too_long"
    if _LEAK.search(fold(question)):
        return "score_leak"
    if is_repeat(question, asked):
        return "repeat"
    return None


class QuestionStream:
    def __init__(self, spec: QuestionSpec, interviewer, asked: List[str],
                 collector: Optional[UsageCollector] = None, first_token_timeout: float = FIRST_TOKEN_TIMEOUT_S):
        self.spec, self.interviewer, self.asked, self.collector = spec, interviewer, asked, collector
        self.first_token_timeout = first_token_timeout
        self.question, self.source = "", "ai"

    def _fallback(self, reason: str) -> str:
        log.warning("interviewer_fallback action=%s reason=%s", self.spec.action, reason)
        if self.collector is not None:
            self.collector.add(CallRecord("interviewer", "fallback", fallback="interviewer_fallback"))
        self.source = "fallback"
        self.question = fallback_question(self.spec)
        return self.question

    async def events(self) -> AsyncIterator[Tuple[str, dict]]:
        parts: List[str] = []
        gen = self.interviewer.stream(self.spec, self.collector).__aiter__()
        try:
            first = await asyncio.wait_for(gen.__anext__(), timeout=self.first_token_timeout)
            parts.append(first)
            yield "token", {"t": first}
            async for piece in gen:
                parts.append(piece)
                yield "token", {"t": piece}
        except StopAsyncIteration:
            pass  # stream rong: xu ly o buoc kiem ben duoi
        except Exception as err:  # loi LLM / mang / timeout: phien khong duoc chet (FR-AI-071)
            if not parts:
                for tok in chunk_tokens(self._fallback(f"before_first_token:{type(err).__name__}")):
                    yield "token", {"t": tok}
                return
            yield "replace", {"question": self._fallback(f"mid_stream:{type(err).__name__}")}
            return
        finally:
            await _close(gen)
        raw = "".join(parts)
        self.question = clean_question(raw)
        problem = violation(self.question, self.asked)
        if problem and self.question == fallback_question(self.spec):
            problem = None  # cau mau (mock) trung chinh no: thay bang no cung vo ich
        if problem and not parts:
            for tok in chunk_tokens(self._fallback(problem)):
                yield "token", {"t": tok}
        elif problem:
            yield "replace", {"question": self._fallback(problem)}
        elif self.question != raw.strip():  # da bo markdown: client hien dung cau da lam sach
            yield "replace", {"question": self.question}


async def _close(gen) -> None:
    aclose = getattr(gen, "aclose", None)
    if aclose:
        try:
            await aclose()
        except Exception:  # dong generator da loi: bo qua
            pass
