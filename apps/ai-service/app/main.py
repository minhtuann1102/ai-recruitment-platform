"""AI Interview Service (MOCK). Contract: docs/ai-service/06-api-contract.md muc 7.4.

Mock dung quy tac thay cho LLM de FSD tich hop truoc; hinh dang request/response/SSE la that.
"""
import logging
import time
from typing import Callable, Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from .api_error import ApiError
from .llm.usage import UsageCollector
from .agents.cv_parser import get_cv_parser
from .agents.jd_parser import get_jd_parser
from .mock_planner import load_track
from .models_cv import CvParseResponse
from .models_jd import JdParseRequest, JdParseResponse
from .models_interview import FinalizeRequest, NextTurnRequest, StartRequest
from .agents.reporter import get_reporter
from .agents.interviewer import get_interviewer
from .question_stream import QuestionStream
from .dev_play_page import router as dev_play_router
from .security import internal_token_middleware
from .sse import SSE_HEADERS, event
from .turn_engine import TurnResult, finish_turn, next_turn, start_session

MODEL = "mock-v2"
log = logging.getLogger("ai_service")
app = FastAPI(title="AI Interview Service (Mock)", version="0.2.0")
app.middleware("http")(internal_token_middleware)
app.include_router(dev_play_router)  # GET /dev/play: trang phong van thu cho dev


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
    return {"status": "healthy", "version": MODEL, "model_loaded": False}


@app.post("/api/cv/parse", response_model=CvParseResponse)
async def cv_parse(file: UploadFile = File(...), track: str = Form(...)):
    load_track(track)  # 422 neu track khong co trong catalog
    return await get_cv_parser().parse(await file.read(), track)


@app.post("/api/jd/parse", response_model=JdParseResponse)
async def jd_parse(req: JdParseRequest):
    """FR-AI-017: JD cua job trong application -> jd_profile cho Planner (JD khong vao RAG)."""
    return await get_jd_parser().parse(req.jd_text, load_track(req.track))


def _usage_meta(started: float, collector: Optional[UsageCollector] = None) -> dict:
    total = int((time.perf_counter() - started) * 1000)
    if collector is None or not collector.records:
        return {"usage": {}, "latency_ms": {"total": total}, "prompt_versions": {"mock": MODEL}, "fallbacks": []}
    meta = collector.to_metadata()
    meta["latency_ms"]["total"] = total  # tong thoi gian request, khong chi thoi gian goi LLM
    return meta


def _stream(result: TurnResult, build_done: Callable[[TurnResult], dict], collector: UsageCollector):
    """meta -> token... (Interviewer stream, co the replace) -> done. `done` dung SAU khi biet cau hoi cuoi."""
    async def gen():
        try:
            if result.meta:
                yield event("meta", result.meta)
            if result.spec is not None:
                qs = QuestionStream(result.spec, get_interviewer(), result.state.asked_questions, collector)
                async for name, data in qs.events():
                    yield event(name, data)
                finish_turn(result, qs.question, qs.source)
            yield event("done", build_done(result))
        except Exception:  # loi ngoai du kien: bao error de interview-service cho gui lai (FR-AI-039)
            log.exception("stream_failed")
            yield event("error", {"errorCode": "AI_SERVICE_ERROR", "message": "AI tạm thời không phản hồi",
                                  "retryable": True})
    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/start")
async def start(req: StartRequest):
    started, collector = time.perf_counter(), UsageCollector()
    r = await start_session(req, collector=collector)
    return _stream(r, lambda x: {"question": x.question, "turn": x.turn.model_dump(), "plan": x.plan.model_dump(),
                                 "state": x.state.model_dump(), "metadata": _usage_meta(started, collector)},
                   collector)


@app.post("/api/next-turn")
async def next_turn_route(req: NextTurnRequest):
    started, collector = time.perf_counter(), UsageCollector()
    r = await next_turn(req, collector=collector)
    return _stream(r, lambda x: {
        "evaluation": x.evaluation.model_dump() if x.evaluation else None, "question": x.question,
        "turn": x.turn.model_dump() if x.turn else None, "state": x.state.model_dump(),
        "session_end": x.session_end, "metadata": _usage_meta(started, collector)}, collector)


@app.post("/api/finalize")
async def finalize(req: FinalizeRequest):
    """Code tinh diem -> Reporter viet nhan xet; Reporter loi thi status = partial (van 200, FR-AI-054)."""
    collector = UsageCollector()
    report = await get_reporter().report(req, collector)
    usage = collector.to_metadata()
    report.setdefault("meta", {})["fallbacks"] = usage["fallbacks"]
    # FR-AI-080: token cua Reporter de tinh chi phi ca phien (start + next-turn + finalize)
    report["metadata"] = {**report.get("metadata", {}), "usage": usage["usage"], "latency_ms_by_agent": usage["latency_ms"]}
    return report
