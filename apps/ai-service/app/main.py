"""AI Interview Service (MOCK). Contract: docs/ai-service/06-api-contract.md muc 7.4.

Mock dung quy tac thay cho LLM de FSD tich hop truoc; hinh dang request/response/SSE la that.
"""
import time
from typing import Optional

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
from .report_scoring import build_report
from .sse import SSE_HEADERS, stream_events
from .turn_engine import TurnResult, next_turn, start_session

MODEL = "mock-v2"
app = FastAPI(title="AI Interview Service (Mock)", version="0.2.0")


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


def _stream(result: TurnResult, done: dict):
    return StreamingResponse(stream_events(result.meta or None, result.question, done),
                             media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/start")
def start(req: StartRequest):
    started = time.perf_counter()
    r = start_session(req)
    done = {"question": r.question, "turn": r.turn.model_dump(), "plan": r.plan.model_dump(),
            "state": r.state.model_dump(), "metadata": _usage_meta(started)}
    return _stream(r, done)


@app.post("/api/next-turn")
async def next_turn_route(req: NextTurnRequest):
    started, collector = time.perf_counter(), UsageCollector()
    r = await next_turn(req, collector=collector)
    done = {"evaluation": r.evaluation.model_dump() if r.evaluation else None, "question": r.question,
            "turn": r.turn.model_dump() if r.turn else None, "state": r.state.model_dump(),
            "session_end": r.session_end, "metadata": _usage_meta(started, collector)}
    return _stream(r, done)


@app.post("/api/finalize")
def finalize(req: FinalizeRequest):
    return build_report(req)
