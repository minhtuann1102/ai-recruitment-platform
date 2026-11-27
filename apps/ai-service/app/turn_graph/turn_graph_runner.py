"""Chay graph mot luot cho endpoint SSE, giu dung ma loi HTTP va huy duoc khi client ngat.

Truoc LangGraph, next_turn() chay xong TRUOC khi tao StreamingResponse nen 409 / 422 tra JSON dung ma. Graph chay ca
Interviewer (node `ask`) nen endpoint `prime()` truoc: chay toi event dau tien cua `ask` (hoac toi khi graph xong) -
moi buoc perceive / evaluate / decide / act da chay, loi cua chung no ra trong handler nhu cu.

Graph chay trong mot task asyncio rieng (pump) day event vao hang doi, khong chay truc tiep trong generator cua
response: khi client ngat, Starlette huy generator bang cancel scope cua anyio, `astream` bi ngat giua chung va LangGraph
khong kip huy task cua node -> Interviewer chay tiep trong nen toi het cau (review phase 02, M1). Huy task pump
(`aclose`) thi LangGraph don dep binh thuong va dong Interviewer. Task tao bang create_task nen mang theo contextvars
cua handler (bind_request, tracing).

Phase 03: graph co checkpointer, chay tren thread cua phien (thread_id = session_id) voi durability="exit" - mot lan
ghi checkpoint khi graph xong. `on_finish` (nha khoa phien, goi nhieu lan khong sao) goi khi task pump ket thuc vi bat
ky ly do gi va o aclose: luc do checkpoint da ghi (hoac luot da huy), request sau cua phien doc dung state.
"""
import asyncio
from typing import Any, AsyncIterator, Callable, Optional, Tuple

from ..session_store.session_checkpointer import thread_config
from ..turn_result import TurnResult
from ..turn_steps import TurnContext

_END = object()  # graph chay xong


class GraphTurnRun:
    def __init__(self, graph, ctx: TurnContext, on_finish: Optional[Callable[[], None]] = None,
                 graph_input: Any = None, config: Optional[dict] = None):
        """Graph ca phien (phase 05): ctx la SessionRunContext (co .result), graph_input = {} (/start) hoac
        Command(resume=...), config co the tro checkpoint_id de resume tu diem cho (session_resume_point)."""
        self.ctx = ctx
        self._input = {} if graph_input is None else graph_input
        self._config = config or thread_config(ctx.req.session_id)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._first: Optional[Tuple[str, dict]] = None
        self._on_finish = on_finish
        self._task = asyncio.create_task(self._pump(graph))

    async def _pump(self, graph) -> None:
        try:
            # input {} (khong phai None): luon chay luot moi tu START, ke ca khi checkpoint truoc dung giua `ask`
            async for item in graph.astream(self._input, self._config, context=self.ctx,
                                            stream_mode="custom", durability="exit"):
                self._queue.put_nowait(item)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # loi trong node (ApiError cua perceive, loi Interviewer...): chuyen cho ben doc
            self._queue.put_nowait(err)
        else:
            self._queue.put_nowait(_END)
        finally:
            if self._on_finish is not None:
                self._on_finish()

    async def _next(self) -> Optional[Tuple[str, dict]]:
        item = await self._queue.get()
        if item is _END:
            return None
        if isinstance(item, Exception):
            raise item  # giu nguyen kieu loi: exception_handler cua ApiError van ra dung ma HTTP
        return item

    async def prime(self) -> None:
        """Chay toi event dau (meta / token cua `ask`) hoac het graph; loi cua perceive... no tai day."""
        try:
            self._first = await self._next()
        except BaseException:  # loi hoac handler bi huy: khong de graph chay tiep
            await self.aclose()
            raise

    async def events(self) -> AsyncIterator[Tuple[str, dict]]:
        item = self._first
        while item is not None:
            yield item
            item = await self._next()

    @property
    def result(self) -> TurnResult:
        return self.ctx.result  # graph sua ctx tai cho; doc sau khi events() het

    async def aclose(self) -> None:
        """Huy graph (neu con chay) va cho no don dep xong; goi nhieu lan khong sao."""
        if not self._task.done():
            self._task.cancel()
        try:
            await self._task
        except BaseException:  # CancelledError cua task pump (hoac huy tu ben ngoai): da xu ly xong
            pass
        if self._on_finish is not None:  # task bi huy truoc khi kip chay thi finally cua pump khong chay
            self._on_finish()
