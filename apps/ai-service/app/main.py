"""AI Interview Service (MOCK). Contract: docs/ai-service/06-api-contract.md muc 7.4.

Mock dung quy tac thay cho LLM de FSD tich hop truoc; hinh dang request/response/SSE la that.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api_error import ApiError
from .logging_setup import configure_logging
from .interview_session_routes import router as interview_router
from .request_lifecycle_telemetry import MODEL, finish_request, logged_failure
from .llm.usage import CallRecord, UsageCollector
from .agents.cv_parser import get_cv_parser
from .agents.registry import agent_status, check_agent_config
from .agents.jd_parser import get_jd_parser
from .mock_planner import load_track
from .models_cv import CvParseResponse
from .models_jd import JdParseRequest, JdParseResponse
from .plan_snippets import close_rag, rag_status, warm_rag
from .dev_interview_page import router as dev_interview_router
from .dev_play_page import router as dev_play_router
from .dev_voice_proxy import router as dev_voice_router
from .matching.router import router as match_router
from .matching.service import get_match_service
from .security import internal_token_middleware
from .stt_phrase_hints import track_phrases
from . import metrics, tracing
from .session_store.session_checkpointer import close_session_store, open_session_store
from .session_store.session_graph_settings import load_session_graph_mode
from .turn_graph.session_graph_selector import session_graph

TRACE_FLUSH_TIMEOUT_S = 5.0
configure_logging()  # truoc moi log: uvicorn khong cau hinh logger ai_service
log = logging.getLogger("ai_service")


@asynccontextmanager
async def lifespan(_: FastAPI):
    check_agent_config()  # staging/production thieu cau hinh LLM: khong khoi dong
    get_match_service()  # MATCH_WEIGHTS... sai: khong khoi dong (017); khong cham DB, chi muc nap o request dau
    tracing.warm()
    await open_session_store()  # SESSION_STORE sai: khong khoi dong; truoc khi compile graph (graph giu checkpointer)
    load_session_graph_mode()  # SESSION_GRAPH sai: khong khoi dong
    session_graph()  # compile graph (mot luot hoac ca phien theo SESSION_GRAPH) luc khoi dong, request dau khong chiu
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
# truoc dev_play_router: route /dev/{name} cua /dev/play se nuot mat /dev/interview
app.include_router(dev_interview_router)  # GET /dev/interview: phong van thu bang giong noi (dev)
app.include_router(dev_voice_router)  # /dev/voice/*: proxy voice-service cho trang tren (dev, can token)
app.include_router(dev_play_router)  # GET /dev/play: trang phong van thu cho dev
app.include_router(interview_router)  # /api/start, /api/next-turn, /api/finalize (app/interview_session_routes.py)
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
    with logged_failure("cv_parse", started, collector, rag="-"):
        result = await get_cv_parser().parse(await file.read(), track)
        _note_parser_fallbacks("cv_parser", result, collector)
    finish_request("cv_parse", started, collector, "ok", rag="-")
    return result


@app.post("/api/jd/parse", response_model=JdParseResponse)
async def jd_parse(req: JdParseRequest):
    """FR-AI-017: JD cua job trong application -> jd_profile cho Planner (JD khong vao RAG)."""
    tracing.start_request("jd_parse", tags=[req.track])
    started, collector = time.perf_counter(), UsageCollector()
    with logged_failure("jd_parse", started, collector, rag="-"):
        result = await get_jd_parser().parse(req.jd_text, load_track(req.track))
        _note_parser_fallbacks("jd_parser", result, collector)
    finish_request("jd_parse", started, collector, "ok", rag="-")
    return result


def _note_parser_fallbacks(agent: str, result, collector: UsageCollector) -> None:
    """CV/JD Parser bao fallback trong metadata cua response; dua vao collector de co trong log request_done."""
    for code in result.metadata.fallbacks:
        collector.add(CallRecord(agent, result.metadata.model, fallback=code))


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    """So lieu Prometheus (app/metrics.py); can X-Internal-Token nhu cac endpoint khac."""
    return metrics.metrics_endpoint()


@app.get("/api/stt/phrases")
async def stt_phrases(track: str):
    """Thuat ngu goi y cho dich vu STT theo track (phrase list / prompt), khong goi LLM."""
    return {"track": track, "phrases": list(track_phrases(track))}
