"""AI Interview Service (MOCK). Contract: docs/ai-service/06-api-contract.md muc 7.4.

Mock dung quy tac thay cho LLM de FSD tich hop truoc; hinh dang request/response/SSE la that.
"""
import asyncio
import logging
import time
from contextlib import aclosing, asynccontextmanager, contextmanager
from typing import AsyncIterator, Awaitable, Callable, Optional, Tuple

import anyio
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from .api_error import ApiError
from .llm.usage import CallRecord, UsageCollector
from .logging_setup import bind_request, configure_logging, safe_session_id
from .agents.cv_parser import get_cv_parser
from .agents.registry import agent_status, check_agent_config
from .agents.jd_parser import get_jd_parser
from .mock_planner import load_track
from .models_cv import CvParseResponse
from .models_jd import JdParseRequest, JdParseResponse
from .models_interview import FinalizeRequest, NextTurnRequest, StartRequest
from .agents.reporter import get_reporter
from .agents.interviewer import get_interviewer
from .plan_snippets import close_rag, note_rag_errors, rag_status, warm_rag
from .question_stream import turn_question_events
from .dev_play_page import router as dev_play_router
from .matching.router import router as match_router
from .matching.service import get_match_service
from .security import internal_token_middleware
from .sse import SSE_HEADERS, event
from .stt_phrase_hints import track_phrases
from . import metrics, tracing
from .replan import effective_plan
from .session_store.session_checkpointer import close_session_store, open_session_store
from .session_store.session_lock import turn_locks
from .session_store.session_record import record_start
from .session_store.session_turn_guard import check_turn, replay_events
from .turn_engine import TurnResult, start_session, turn_context
from .turn_result import turn_payload
from .turn_graph.turn_graph_builder import turn_graph
from .turn_graph.turn_graph_runner import GraphTurnRun

MODEL = "mock-v2"
TRACE_FLUSH_TIMEOUT_S = 5.0
configure_logging()  # truoc moi log: uvicorn khong cau hinh logger ai_service
log = logging.getLogger("ai_service")


@asynccontextmanager
async def lifespan(_: FastAPI):
    check_agent_config()  # staging/production thieu cau hinh LLM: khong khoi dong
    get_match_service()  # MATCH_WEIGHTS... sai: khong khoi dong (017); khong cham DB, chi muc nap o request dau
    tracing.warm()
    await open_session_store()  # SESSION_STORE sai: khong khoi dong; truoc khi compile graph (graph giu checkpointer)
    turn_graph()  # compile graph mot luot luc khoi dong, request dau khong chiu
    warm = asyncio.ensure_future(warm_rag())  # khong chan khoi dong: nap corpus BM25 o nen
    yield
    warm.cancel()
    await close_rag()
    await close_session_store()
    try:  # flush trace co the treo neu Langfuse khong toi duoc: khong giu service luc tat
        await asyncio.wait_for(asyncio.to_thread(tracing.shutdown), TRACE_FLUSH_TIMEOUT_S)
    except asyncio.TimeoutError:
        log.warning("tracing_flush_timeout timeout_s=%s", TRACE_FLUSH_TIMEOUT_S)


app = FastAPI(title="AI Interview Service (Mock)", version="0.2.0", lifespan=lifespan)
app.middleware("http")(internal_token_middleware)
app.middleware("http")(metrics.metrics_middleware)  # dang ky sau = boc ngoai: dem ca 401 cua token
app.include_router(dev_play_router)  # GET /dev/play: trang phong van thu cho dev
app.include_router(match_router)  # POST /api/match/jobs: goi y viec lam theo CV (017, noi bo)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": exc.error, "message": exc.message, "details": exc.details})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    errors = [{"loc": [str(p) for p in e["loc"]], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    first = errors[0] if errors else {"loc": [], "msg": "invalid request"}
    field = ".".join(p for p in first["loc"] if p != "body")
    return JSONResponse(status_code=422, content={
        "error": "invalid_request", "message": f"{field}: {first['msg']}", "details": {"errors": errors}})


@app.get("/api/health")
def health():
    # RAG tuy chon: loi RAG khong lam service unhealthy (van 200), chi bao trong `rag`. Khong ping ai_db o day.
    # Agent thieu cau hinh: service van tra loi duoc nhung bang mock nen `degraded`, van 200 (bao o `agents`).
    agents = agent_status()
    status = "degraded" if "config_error" in agents.values() else "healthy"
    return {"status": status, "version": MODEL, "model_loaded": False, "rag": rag_status(), "agents": agents}


@app.post("/api/cv/parse", response_model=CvParseResponse)
async def cv_parse(file: UploadFile = File(...), track: str = Form(...)):
    load_track(track)  # 422 neu track khong co trong catalog
    tracing.start_request("cv_parse", tags=[track])
    started, collector = time.perf_counter(), UsageCollector()
    with _logged_failure("cv_parse", started, collector, rag="-"):
        result = await get_cv_parser().parse(await file.read(), track)
        _note_parser_fallbacks("cv_parser", result, collector)
    _finish_request("cv_parse", started, collector, "ok", rag="-")
    return result


@app.post("/api/jd/parse", response_model=JdParseResponse)
async def jd_parse(req: JdParseRequest):
    """FR-AI-017: JD cua job trong application -> jd_profile cho Planner (JD khong vao RAG)."""
    tracing.start_request("jd_parse", tags=[req.track])
    started, collector = time.perf_counter(), UsageCollector()
    with _logged_failure("jd_parse", started, collector, rag="-"):
        result = await get_jd_parser().parse(req.jd_text, load_track(req.track))
        _note_parser_fallbacks("jd_parser", result, collector)
    _finish_request("jd_parse", started, collector, "ok", rag="-")
    return result


def _note_parser_fallbacks(agent: str, result, collector: UsageCollector) -> None:
    """CV/JD Parser bao fallback trong metadata cua response; dua vao collector de co trong log request_done."""
    for code in result.metadata.fallbacks:
        collector.add(CallRecord(agent, result.metadata.model, fallback=code))


def _usage_meta(started: float, collector: Optional[UsageCollector] = None) -> dict:
    total = int((time.perf_counter() - started) * 1000)
    if collector is None or not collector.records:
        meta = {"usage": {}, "latency_ms": {"total": total}, "prompt_versions": {"mock": MODEL}, "fallbacks": []}
    else:
        meta = collector.to_metadata()
        meta["latency_ms"]["total"] = total  # tong thoi gian request, khong chi thoi gian goi LLM
    # RAG bat mac dinh: loi thi phien chay khong co RAG, bao o day (status error + fallback rag_unavailable)
    meta["rag"] = rag_status(collector)
    note_rag_errors(collector)  # sau khi bao: ngat RAG tam thoi cho cac request sau
    if meta["rag"]["status"] == "error":
        meta["fallbacks"].append("rag_unavailable")
    return meta


def _finish_request(endpoint: str, started: float, collector: UsageCollector, status: str, error: str = "-",
                    rag: Optional[str] = None, error_code: Optional[str] = None) -> None:
    """Dong tong ket moi request, ca khi loi (lam so lieu TTFT / fallback / RAG tu log; chi so do va ma) + dong trace
    + so lieu Prometheus. `rag`: trang thai da bao trong metadata (giu dung gia tri do); None thi tinh lai tu
    collector. `error_code`: ma loi API (voice_no_speech...) cho nhan so lieu, log van ghi ten loi."""
    fallbacks = ",".join(r.fallback for r in collector.records if r.fallback) or "-"
    rag = rag or rag_status(collector)["status"]
    seconds = time.perf_counter() - started
    log.info("request_done status=%s error=%s ms=%d tokens=%d fallbacks=%s rag=%s trace=%s", status, error,
             seconds * 1000, collector.total_tokens(), fallbacks, rag, tracing.trace_id() or "-")
    tracing.finish_request(status, error, fallbacks=fallbacks, rag=rag)
    metrics.record_request(endpoint, status, error_code or error, seconds, collector, rag)


@contextmanager
def _logged_failure(endpoint: str, started: float, collector: UsageCollector, rag: Optional[str] = None):
    """Loi truoc khi stream (ApiError 409/422, loi ngoai du kien): van ghi request_done roi nem tiep."""
    try:
        yield
    except BaseException as err:
        status = "cancelled" if isinstance(err, asyncio.CancelledError) else "error"
        code = err.error if isinstance(err, ApiError) else None
        _finish_request(endpoint, started, collector, status, type(err).__name__, rag, error_code=code)
        raise


class _TurnStream(StreamingResponse):
    """Client ngat: Starlette huy task stream ma khong dong generator (chi GC dong, trong context bat ky, co khi cua
    request khac). Dong generator va tong ket request ngay tai day, trong context cua chinh request nay; generator
    chua kip chay cung qua day."""

    def __init__(self, content, on_close: Callable[[], None], cleanup: Optional[Callable[[], Awaitable]] = None):
        super().__init__(content, media_type="text/event-stream", headers=SSE_HEADERS)
        self._on_close, self._cleanup = on_close, cleanup

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                with anyio.CancelScope(shield=True):
                    await self.body_iterator.aclose()
                    if self._cleanup is not None:  # graph da chay truoc response (prime): huy ca khi generator chua chay
                        await self._cleanup()
            finally:
                self._on_close()


def _stream(endpoint: str, turn_events: AsyncIterator[Tuple[str, dict]], result_of: Callable[[], TurnResult],
            build_done: Callable[[TurnResult], dict], collector: UsageCollector, started: float,
            cleanup: Optional[Callable[[], Awaitable]] = None):
    """meta -> token... (Interviewer stream, co the replace) -> done. `turn_events` goi finish_turn khi het (cau hoi
    that da ghi vao state); `done` dung SAU do tu `result_of()`."""
    outcome = {"status": "cancelled", "error": "-", "rag": None}  # client ngat: khong qua hai nhanh gan ben duoi

    async def gen():
        try:
            ttft = None  # chu dau tien cua cau hoi toi client; ghi sau stream khi da biet nguon cau hoi
            async with aclosing(turn_events) as events:
                async for name, data in events:
                    if ttft is None and name in ("token", "replace"):
                        ttft = time.perf_counter() - started
                    yield event(name, data)
            result = result_of()
            if ttft is not None and result is not None:  # replay (result None): khong do TTFT, khong goi LLM
                metrics.observe_ttft(endpoint, result.source, ttft)
            done = build_done(result)
            outcome.update(status="ok", rag=done["metadata"]["rag"]["status"])
            tracing.set_output(done.get("question"))
            yield event("done", done)
        except Exception as err:  # loi ngoai du kien: bao error de interview-service cho gui lai (FR-AI-039)
            outcome.update(status="error", error=type(err).__name__)
            log.exception("stream_failed")
            yield event("error", {"errorCode": "AI_SERVICE_ERROR", "message": "AI tạm thời không phản hồi",
                                  "retryable": True})
    return _TurnStream(gen(), lambda: _finish_request(endpoint, started, collector, **outcome), cleanup)


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    """So lieu Prometheus (app/metrics.py); can X-Internal-Token nhu cac endpoint khac."""
    return metrics.metrics_endpoint()


@app.get("/api/stt/phrases")
async def stt_phrases(track: str):
    """Thuat ngu goi y cho dich vu STT theo track (phrase list / prompt), khong goi LLM."""
    return {"track": track, "phrases": list(track_phrases(track))}


@app.post("/api/start")
async def start(req: StartRequest):
    bind_request(req.session_id)
    tracing.start_request("start", session_id=safe_session_id(req.session_id), tags=[req.track, req.level])
    started, collector = time.perf_counter(), UsageCollector()
    with _logged_failure("start", started, collector):
        release = turn_locks.hold(req.session_id)  # luot dang chay cua phien cu ghi muon thi de mat checkpoint moi
        try:
            r = await start_session(req, collector=collector)
        except BaseException:
            release()
            raise

    async def events():  # cau hoi dau gui xong moi ghi checkpoint dau cua phien (stream dut: /start gui lai)
        try:
            async with aclosing(turn_question_events(r, get_interviewer, collector)) as question_events:
                async for item in question_events:
                    yield item
            await record_start(turn_graph(), req, r)  # loi ghi chi log, van gui done
        finally:
            release()

    async def cleanup():  # client ngat truoc khi generator chay: van nha khoa
        release()
    return _stream("start", events(), lambda: r, lambda x: {
        "question": x.question, "turn": x.turn.model_dump(), "plan": x.plan.model_dump(),
        "state": x.state.model_dump(), "metadata": _usage_meta(started, collector)}, collector, started, cleanup)


@app.post("/api/next-turn")
async def next_turn_route(req: NextTurnRequest):
    bind_request(req.session_id, req.turn_number)
    tracing.start_request("next_turn", session_id=safe_session_id(req.session_id), turn_number=req.turn_number,
                          tags=[req.track, req.level], input={"question": req.question, "answer": req.answer})
    started, collector = time.perf_counter(), UsageCollector()
    with _logged_failure("next_turn", started, collector):
        release = turn_locks.hold(req.session_id)  # 409 turn_in_progress; nha khi graph xong (hoac loi / replay)
        replay = run = None
        try:
            # app/session_store: luot da xong -> replay; sai thu tu / phien done -> 409; doc checkpoint loi -> 503
            replay = await check_turn(turn_graph(), req)
            if replay is None:
                # graph LangGraph (app/turn_graph): chay toi event dau cua Interviewer truoc khi mo response, nen
                # loi perceive (409 / 422) van tra dung ma HTTP; Evaluator lay tu turn_engine (test / evals patch)
                run = GraphTurnRun(turn_graph(), turn_context(req, collector=collector, interviewer=get_interviewer),
                                   on_finish=release)
                await run.prime()
        finally:
            if run is None:  # replay / loi truoc khi chay graph; co graph thi runner nha khoa khi xong
                release()
    if replay is not None:  # luot gui lai sau khi da xong: tra dung `done` cu, metadata danh dau replayed
        return _stream("next_turn", replay_events(replay), lambda: None, lambda _: {
            **replay["done"], "metadata": {**_usage_meta(started, collector), "replayed": True}}, collector, started)

    def done(x: TurnResult) -> dict:  # chi goi khi stream toi done: luot loi / bi ngat khong vao ai_turns
        metrics.record_turn(req.answer_source, x.evaluation)
        return {**turn_payload(x), "metadata": _usage_meta(started, collector)}
    return _stream("next_turn", run.events(), lambda: run.result, done, collector, started, run.aclose)


@app.post("/api/finalize")
async def finalize(req: FinalizeRequest):
    """Code tinh diem -> Reporter viet nhan xet; Reporter loi thi status = partial (van 200, FR-AI-054)."""
    bind_request(req.session_id)
    tracing.start_request("finalize", session_id=safe_session_id(req.session_id), tags=[req.track, req.level])
    started, collector = time.perf_counter(), UsageCollector()
    with _logged_failure("finalize", started, collector, rag="-"):  # finalize khong dung RAG
        # phase 05: topic da doi (state.swaps) thanh plan thuc te truoc khi cham diem / bao cao; plan cu y nguyen
        req = req.model_copy(update={"plan": effective_plan(req.plan, req.state)})
        report = await get_reporter().report(req, collector)
        usage = collector.to_metadata()
        report.setdefault("meta", {})["fallbacks"] = usage["fallbacks"]
        # FR-AI-080: token cua Reporter de tinh chi phi ca phien (start + next-turn + finalize)
        report["metadata"] = {**report.get("metadata", {}), "usage": usage["usage"],
                              "latency_ms_by_agent": usage["latency_ms"]}
        tracing.set_output(report.get("overall"))
    _finish_request("finalize", started, collector, "ok", rag="-")
    return report
