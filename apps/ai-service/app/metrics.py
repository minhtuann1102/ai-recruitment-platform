"""So lieu Prometheus cua ai-service (GET /metrics, NFR-AI-OBS03): request, do tre, TTFT, lan goi agent, token, RAG,
ket qua cham tung luot. Grafana ve va canh bao tu day; Langfuse van la noi xem tung trace.

Chi so do va ma (endpoint, agent, ma fallback / loi, answer_type), khong co noi dung hay session_id: nhan it gia tri
de khong lam no so chuoi thoi gian. Dockerfile chay mot process uvicorn nen dung REGISTRY mac dinh (kem so lieu
process: CPU, RAM, file mo). Chay nhieu worker thi phai doi sang che do multiprocess cua prometheus_client.
"""
import functools
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, disable_created_metrics, generate_latest
from starlette.routing import Match

from .llm.usage import UsageCollector
from .models_interview import Evaluation

log = logging.getLogger("ai_service.metrics")
disable_created_metrics()  # bo series *_created (moc tao counter): khong dung, chi lam day /metrics
_SLOW = (0.25, 0.5, 1, 2, 3, 5, 8, 13, 20, 30, 60, 120)  # giay: ca request (SSE toi het stream), mot lan goi LLM
_FAST = (0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 8, 13)  # giay: TTFT

HTTP = Counter("ai_http_responses", "Response HTTP theo route va ma (ca 401/422 truoc route, 500 loi ngoai du kien); "
               "SSE dem 200 luc gui header, ket qua stream xem ai_requests",
               ["route", "code"])
REQUESTS = Counter("ai_requests", "Request AI da xong: status ok/error/cancelled, error la ma loi API hoac ten loi",
                   ["endpoint", "status", "error"])
DURATION = Histogram("ai_request_duration_seconds", "Thoi gian request; SSE tinh toi het stream", ["endpoint"],
                     buckets=_SLOW)
TTFT = Histogram("ai_ttft_seconds", "Tu luc nhan request toi token cau hoi dau tien (SSE start, next-turn); "
                 "source = ai (Interviewer viet) / fallback (cau du phong, cau hoi lai co dinh)",
                 ["endpoint", "source"], buckets=_FAST)
AGENT_CALLS = Counter("ai_agent_calls", "Lan goi agent; fallback=none la chay binh thuong", ["agent", "fallback"])
AGENT_LATENCY = Histogram("ai_agent_latency_seconds", "Do tre mot lan goi LLM cua agent", ["agent"], buckets=_SLOW)
TOKENS = Counter("ai_tokens", "Token theo agent; kind = input / output / cached (phan input doc tu cache)",
                 ["agent", "kind"])
TOOL_CALLS = Counter("ai_llm_tool_calls", "Lan agent goi cong cu trong vong lap tool calling cua gateway", ["agent"])
TOOLS_UNSUPPORTED = Counter("ai_llm_tools_unsupported", "Lan model/provider tu choi tools + JSON strict (latch theo "
                            "tien trinh: cac luot sau khong thu lai)")
EVALUATOR_LOOKUP = Counter("ai_evaluator_lookup", "Evaluator tra cuu kho (EVALUATOR_TOOLS): hit / empty / error (query bi "
                           "tu choi) / fallback (vong lap loi, cham lai mot lan khong tools) / budget_exhausted (vong lap loi, het ngan sach nen thang sang mock) / unsupported (latch tools)",
                           ["result"])
POLICY_DECISIONS = Counter("ai_policy_decisions", "Quyet dinh hanh dong moi luot khi POLICY_MODE=hybrid: llm (de xuat "
                           "da qua kiem) / policy (luat, do bac hoac khong co de xuat) / forced (thoi gian, turn cap, "
                           "low_performance)", ["decided_by"])
POLICY_OVERRULES = Counter("ai_policy_overrules", "Ly do code bac de xuat cua LLM (hybrid): no_proposal / sensitive_kind / "
                           "action_not_allowed / no_valid_focus", ["reason"])
REPLAN_SWAPS = Counter("ai_replan_swaps", "Evaluator v10 de xuat doi topic (REPLAN_ENABLED) va ket qua sau khi code kiem: "
                       "applied / budget / bad_drop / jd_priority / bad_add / not_applicable / untrusted", ["result"])
NOTES_DROPPED = Counter("ai_notes_dropped", "Ghi chu agent (AGENT_NOTES_ENABLED) bi code bo: untrusted / empty / injection / "
                        "pii / too_long / invalid_kind / duplicate / full / unknown_id / bad_status", ["reason"])
NOTES_RECORDED = Counter("ai_notes_recorded", "Ghi chu agent (AGENT_NOTES_ENABLED) da luu sau khi qua kiem, theo kind", ["kind"])
RAG = Counter("ai_rag_requests", "Trang thai RAG bao trong metadata cua request co dung RAG", ["status"])
RAG_ERRORS = Counter("ai_rag_errors", "Ma loi RAG trong request (rag_timeout, rag_db_error...)", ["code"])
TURNS = Counter("ai_turns", "Ket qua cham moi luot next-turn stream xong (luot wrap-up khong cham thi khong dem): "
                "answer_type, degraded hoac low_confidence (voice)",
                ["answer_source", "outcome"])


def _safe(fn):
    """So lieu loi khong duoc che loi that cua request hay lam hong luc dong stream: ghi log roi bo qua."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        except Exception:
            log.exception("metrics_failed fn=%s", fn.__name__)
    return wrapper


@_safe
def record_request(endpoint: str, status: str, error: str, seconds: float, collector: UsageCollector,
                   rag: Optional[str]) -> None:
    """Goi mot lan khi request ket thuc (main._finish_request), ca khi loi hay client ngat."""
    REQUESTS.labels(endpoint, status, error).inc()
    DURATION.labels(endpoint).observe(seconds)
    for r in collector.records:
        AGENT_CALLS.labels(r.agent, r.fallback or "none").inc()
        if r.latency_ms:
            AGENT_LATENCY.labels(r.agent).observe(r.latency_ms / 1000)
        if r.tool_calls:
            TOOL_CALLS.labels(r.agent).inc(r.tool_calls)
        for kind, n in (("input", r.input_tokens), ("output", r.output_tokens), ("cached", r.cached_tokens)):
            if n:
                TOKENS.labels(r.agent, kind).inc(n)
    if rag and rag != "-":  # "-": endpoint khong dung RAG (cv/jd parse, finalize)
        RAG.labels(rag).inc()
    for code in collector.rag_errors:
        RAG_ERRORS.labels(code).inc()


@_safe
def record_tools_unsupported() -> None:
    TOOLS_UNSUPPORTED.inc()


@_safe
def record_evaluator_lookup(result: str) -> None:
    EVALUATOR_LOOKUP.labels(result).inc()


@_safe
def record_policy_decision(decided_by: str, overrule_reason: Optional[str]) -> None:
    POLICY_DECISIONS.labels(decided_by).inc()
    if overrule_reason:
        POLICY_OVERRULES.labels(overrule_reason).inc()


@_safe
def record_replan_swap(result: str) -> None:
    REPLAN_SWAPS.labels(result).inc()


@_safe
def record_note_dropped(reason: str) -> None:
    NOTES_DROPPED.labels(reason).inc()


@_safe
def record_note_recorded(kind: str) -> None:
    NOTES_RECORDED.labels(kind).inc()  # kind da la mot trong 4 gia tri hop le


@_safe
def observe_ttft(endpoint: str, source: str, seconds: float) -> None:
    TTFT.labels(endpoint, source).observe(seconds)


@_safe
def record_turn(answer_source: str, ev: Optional[Evaluation]) -> None:
    if ev is None:
        return
    outcome = "low_confidence" if ev.transcript_low_confidence else "degraded" if ev.degraded else ev.answer_type
    TURNS.labels(answer_source, outcome).inc()


def _route(app: FastAPI, request: Request) -> str:
    """Mau route ("/dev/{name}") thay vi duong dan that: duong dan la khong lam no nhan."""
    for route in app.router.routes:
        if route.matches(request.scope)[0] == Match.FULL:
            return route.path
    return "other"


async def metrics_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:  # loi ngoai du kien: ServerErrorMiddleware tra 500 o ngoai, dem truoc khi nem tiep
        HTTP.labels(_route(request.app, request), "500").inc()
        raise
    HTTP.labels(_route(request.app, request), str(response.status_code)).inc()
    return response


def metrics_endpoint() -> Response:
    """Can X-Internal-Token nhu moi endpoint (tru health): cau hinh scrape gui header nay."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
