"""Evaluator tu tra cuu kho (plans/261114-1549-agentic-ai-service, phase 03): luot khong co dap an chuan (R), Evaluator co
the goi `search_knowledge(query)` de doi chieu mot khang dinh ky thuat cu the truoc khi cham.

LLM chi chon `query`; pham vi tim (category, nguon, do kho, topic) do code co dinh bang cung ham voi RAG theo luot,
BM25 trong bo nho (`memory_only`, < 20 ms, khong cham ai_db). Chunk tra ve duoc boc `wrap_untrusted`, bo chunk da co
(snippet topic + chunk theo luot), <= 3 chunk / <= 600 token. Chunk noi vao cuoi `turn_snippets` nen id tiep tuc
S{n+1}..: hau kiem, trich nguon va bao cao chay nguyen. Chunk cong cu khong co quyen phat (xem postcheck, luat H4).
"""
import functools
import logging
import math
import os
from dataclasses import dataclass, field, replace
from typing import Awaitable, Callable, List, Mapping, Optional, Sequence

from . import metrics
from .agents.evaluator_input import EvaluationInput
from .cv_text import has_injection
from .evaluator_source_checks import label
from .llm.settings import _flag
from .llm.tool_loop import MAX_RESULT_CHARS, tools_supported
from .mock_planner import load_track
from .models_interview import PlanTopic, SourceRef
from .prompts.store import PROMPTS_DIR, wrap_untrusted
from .rag.models import Chunk
from .source_refs import source_ref
from .turn_reference_snippets import TurnChunks, filters_for_turn, search_turn

log = logging.getLogger("ai_service.evaluator")
TOOL_NAME = "search_knowledge"
FRAGMENT = "evaluator_tools.v1"
MAX_CALLS_CAP = 2  # tran cung: moi lan tra cuu them ~1 round trip
SEARCH_TOOL = {"type": "function", "function": {
    "name": TOOL_NAME, "strict": True,
    "description": "Tra kho tài liệu kỹ thuật một khẳng định cụ thể của ứng viên (thuật ngữ ngắn, không chép câu của họ).",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"],
                   "additionalProperties": False}}}
Search = Callable[[str, Sequence[str]], Awaitable[List[Chunk]]]


@dataclass(frozen=True)
class LookupSettings:
    enabled: bool = False
    max_calls: int = 1
    tool_deadline_s: float = 2.0


def _finite(env: Mapping[str, str], name: str, default: float) -> float:
    """So huu han tu env; thieu thi mac dinh, sai dinh dang (chu, nan, inf) thi mac dinh kem canh bao."""
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value):
        log.warning("evaluator_lookup_bad_env name=%s default=%s", name, default)
        return default
    return value


def load_lookup_settings(env: Optional[Mapping[str, str]] = None) -> LookupSettings:
    """Chi doc EVALUATOR_MAX_TOOL_CALLS / _DEADLINE_S khi co bat: go sai khi tat khong duoc anh huong luot cham."""
    env = os.environ if env is None else env
    if not _flag(env.get("EVALUATOR_TOOLS", ""), False):
        return LookupSettings()
    calls = int(_finite(env, "EVALUATOR_MAX_TOOL_CALLS", 1))
    deadline = _finite(env, "EVALUATOR_TOOL_DEADLINE_S", 2.0)
    return LookupSettings(True, max(1, min(calls, MAX_CALLS_CAP)), deadline if deadline > 0 else 2.0)


@functools.lru_cache(maxsize=1)
def fragment_text() -> str:
    """Luat tra cuu, chi noi vao system prompt o luot co tools (prompt chinh van la v8). Doc dia mot lan."""
    return (PROMPTS_DIR / f"{FRAGMENT}.md").read_text(encoding="utf-8")


def _render(start: int, contents: List[str]) -> str:
    return wrap_untrusted("search_results", "\n---\n".join(label(f"S{start + i}", c) for i, c in enumerate(contents)))


@dataclass
class TurnLookup:
    search: Search  # dong: search_turn(..., memory_only=True) voi pham vi co dinh; tham so 2 = chuoi da co
    known_base: List[str]  # snippet topic + chunk theo luot (bo khoi ket qua)
    base_ids: int  # len(all_snippets(inp)): id cong cu bat dau tu S{base_ids + 1}
    settings: LookupSettings = field(default_factory=LookupSettings)
    texts: List[str] = field(default_factory=list)
    sources: List[SourceRef] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    committed: bool = False  # vong lap xong thanh cong: chunk cong cu da vao luot cham (recorder chi doc khi True)

    async def run_tool(self, name: str, args: dict) -> str:
        if name != TOOL_NAME:
            return "error: unknown_tool"
        query = str(args.get("query", ""))
        if has_injection(query):  # query do LLM viet theo cau tra loi cua ung vien: khong de lenh lot vao truy van
            metrics.record_evaluator_lookup("error")
            return "error: invalid_query"
        if query.casefold() in (q.casefold() for q in self.queries):
            return "error: duplicate_query"
        self.queries.append(query)
        chunks = await self.search(query, [*self.known_base, *self.texts])
        if not chunks:
            metrics.record_evaluator_lookup("empty")
            return "Không tìm thấy tài liệu phù hợp."
        contents = [c.content for c in chunks]
        start = self.base_ids + len(self.texts) + 1
        while len(contents) > 1 and len(_render(start, contents)) > MAX_RESULT_CHARS:  # tool_loop cat ket qua o day
            contents.pop()
        if len(_render(start, contents)) > MAX_RESULT_CHARS:
            contents[0] = contents[0][:MAX_RESULT_CHARS - 300] + " ..."
        self.texts += contents
        self.sources += [source_ref(c) for c in chunks[:len(contents)]]
        metrics.record_evaluator_lookup("hit")
        return _render(start, contents)

    def extend(self, inp: EvaluationInput) -> EvaluationInput:
        """Dau vao cua hau kiem: chunk cong cu noi cuoi turn_snippets / turn_sources. Khong co chunk thi giu nguyen."""
        if not self.texts:
            return inp
        return replace(inp, turn_snippets=[*inp.turn_snippets, *self.texts],
                       turn_sources=[*inp.turn_sources, *self.sources], tool_base_ids=self.base_ids)


def build_lookup(retriever, track: str, *, phase: str, topic: PlanTopic, difficulty: int, turn_snippets_: List[str],
                 settings: LookupSettings) -> Optional[TurnLookup]:
    """None khi khong du dieu kien (phase intro, BM25 chua nap, RAG theo luot tat, khong co pham vi, do kho ngoai 1-5,
    latch tools_unsupported). Cac dieu kien theo luot khac (cờ, agent LLM, khong R) do turn_evaluation kiem."""
    hybrid = getattr(retriever, "hybrid", None)
    if (hybrid is None or not getattr(retriever, "turn_retrieval", False) or phase == "intro"
            or not 1 <= difficulty <= 5 or not tools_supported() or hybrid.bm25.ready() is None):
        return None
    filters = filters_for_turn(retriever, phase, topic, load_track(track))
    if filters is None:
        return None

    async def search(query: str, known: Sequence[str]) -> List[Chunk]:
        return await search_turn(retriever, filters, topic, difficulty, query, known, None, True)

    known = [*topic.reference_snippets, *turn_snippets_]
    return TurnLookup(search, known, len(known), settings)


def lookup_for_turn(retriever, track: str, *, phase: str, topic: PlanTopic, difficulty: int, extra: TurnChunks,
                    reference_answer: str, evaluator) -> Optional[TurnLookup]:
    """Cong cua turn_evaluation: co + agent LLM + khong co R + dieu kien build_lookup."""
    settings = load_lookup_settings()
    if not settings.enabled or not getattr(evaluator, "supports_lookup", False) or reference_answer:
        return None
    return build_lookup(retriever, track, phase=phase, topic=topic, difficulty=difficulty,
                        turn_snippets_=extra.texts, settings=settings)

