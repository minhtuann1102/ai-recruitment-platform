"""Endpoint phien phong van: /api/start, /api/next-turn, /api/finalize (docs/ai-service/06 muc 7.4).

Tach khoi main.py (phase 04). next-turn / finalize chi nhan body slim; plan / state / lich su doc tu checkpoint
(app/session_store) va dung lai request noi bo cho turn_engine / Reporter.
"""
import time
from contextlib import aclosing

from fastapi import APIRouter

from . import metrics, tracing
from .agents.interviewer import get_interviewer
from .agents.reporter import get_reporter
from .llm.usage import UsageCollector
from .logging_setup import bind_request, safe_session_id
from .models_interview import StartRequest
from .models_interview_http import FinalizeBody, NextTurnBody
from .question_stream import turn_question_events
from .replan import effective_plan
from .request_lifecycle_telemetry import finish_request, logged_failure, stream_response, usage_meta
from .session_store.session_checkpointer import prune_memory_store
from .session_store.session_graph_settings import session_graph_enabled
from .session_store.session_lock import turn_locks
from .session_store.session_clock import CANDIDATE_ENDED
from .session_store.session_record import record_finalize_end, record_start
from .session_store.session_request_builder import build_finalize_request, build_next_turn_request
from .session_store.session_turn_guard import check_turn, replay_events, stored_snapshot
from .turn_engine import TurnResult, start_session, turn_context
from .turn_graph.session_graph_runs import finalize_run, start_run, turn_run
from .turn_graph.session_graph_selector import session_graph
from .turn_graph.turn_graph_builder import turn_graph
from .turn_graph.turn_graph_runner import GraphTurnRun
from .turn_result import turn_payload

router = APIRouter()


class SessionNotRecorded(RuntimeError):
    """Ghi checkpoint dau cua /start loi: stream bao `error` (retryable) thay vi `done`."""


def trace_on_early_error(endpoint: str, session_id: str, turn_number=None) -> None:
    """Loi truoc khi mo trace (khoa / doc checkpoint / 404): van co trace loi. Khong ghi input (cau tra loi cua ung vien
    khong nen vao Langfuse khi phien khong xac dinh duoc)."""
    if not tracing.trace_id():
        tracing.start_request(endpoint, session_id=safe_session_id(session_id), turn_number=turn_number)


def start_done(started: float, collector: UsageCollector):
    return lambda x: {"question": x.question, "turn": x.turn.model_dump(), "plan": x.plan.model_dump(),
                      "state": x.state.model_dump(), "metadata": usage_meta(started, collector)}


async def with_pruned_memory(run):
    """Stream /start tren graph ca phien: het stream (da ghi checkpoint dau) thi giu store memory trong han."""
    async for item in run.events():
        yield item
    await prune_memory_store()


@router.post("/api/start")
async def start(req: StartRequest):
    bind_request(req.session_id)
    tracing.start_request("start", session_id=safe_session_id(req.session_id), tags=[req.track, req.level])
    started, collector = time.perf_counter(), UsageCollector()
    with logged_failure("start", started, collector):
        release = turn_locks.hold(req.session_id)  # luot dang chay cua phien cu ghi muon thi de mat checkpoint moi
        try:
            if session_graph_enabled():  # graph ca phien: plan -> ask -> record chay trong graph, toi interrupt dau
                run = await start_run(req, collector, get_interviewer, release)
                await run.prime()  # loi Planner... ra truoc khi mo response, nhu duong per_turn
                return stream_response("start", with_pruned_memory(run), lambda: run.result, start_done(started, collector),
                                       collector, started, run.aclose)
            r = await start_session(req, collector=collector)
        except BaseException:
            release()
            raise

    async def events():  # cau hoi dau gui xong moi ghi checkpoint dau cua phien
        try:
            async with aclosing(turn_question_events(r, get_interviewer, collector)) as question_events:
                async for item in question_events:
                    yield item
            # checkpoint la nguon duy nhat cua phien: ghi loi thi bao error (retryable) de FSD goi /start lai ngay,
            # khong de ung vien tra loi cau 1 roi nhan 404
            if not await record_start(turn_graph(), req, r):
                raise SessionNotRecorded("session_not_recorded")
        finally:
            release()

    async def cleanup():  # client ngat truoc khi generator chay: van nha khoa
        release()
    return stream_response("start", events(), lambda: r, start_done(started, collector), collector, started, cleanup)


@router.post("/api/next-turn")
async def next_turn_route(body: NextTurnBody):
    bind_request(body.session_id, body.turn_number)
    started, collector = time.perf_counter(), UsageCollector()
    with logged_failure("next_turn", started, collector):
        replay = run = None
        release = None
        try:
            release = turn_locks.hold(body.session_id)  # 409 turn_in_progress; nha khi graph xong (hoac loi / replay)
            # checkpoint la nguon su that duy nhat: doc loi -> 503, thread chua co / cu -> 404
            snap, stored = await stored_snapshot(session_graph(), body.session_id)
            session = stored["session"]
            tracing.start_request("next_turn", session_id=safe_session_id(body.session_id),
                                  turn_number=body.turn_number, tags=[session["track"], session["level"]],
                                  input={"question": stored["question"], "answer": body.answer})
            # app/session_store: luot da xong -> replay; sai thu tu / phien done -> 409
            replay = await check_turn(stored, body)
            if replay is None:
                req = build_next_turn_request(body, stored)
                # graph LangGraph (app/turn_graph): chay toi event dau cua Interviewer truoc khi mo response, nen
                # loi perceive (409 / 422) van tra dung ma HTTP; Evaluator lay tu turn_engine (test / evals patch)
                if session_graph_enabled():  # graph ca phien: resume tu wait_answer (lui lai neu luot truoc dut)
                    run = await turn_run(req, snap, collector, get_interviewer, release)
                else:
                    run = GraphTurnRun(turn_graph(), turn_context(req, collector=collector,
                                                                  interviewer=get_interviewer), on_finish=release)
                await run.prime()
        except BaseException:
            trace_on_early_error("next_turn", body.session_id, body.turn_number)
            raise
        finally:
            if run is None and release is not None:  # replay / loi truoc khi chay graph; co graph thi runner nha khoa
                release()
    if replay is not None:  # luot gui lai sau khi da xong: tra dung `done` cu, metadata danh dau replayed
        return stream_response("next_turn", replay_events(replay), lambda: None, lambda _: {
            **replay["done"], "metadata": {**usage_meta(started, collector), "replayed": True}}, collector, started)

    def done(x: TurnResult) -> dict:  # chi goi khi stream toi done: luot loi / bi ngat khong vao ai_turns
        metrics.record_turn(body.answer_source, x.evaluation)
        return {**turn_payload(x), "metadata": usage_meta(started, collector)}
    return stream_response("next_turn", run.events(), lambda: run.result, done, collector, started, run.aclose)


@router.post("/api/finalize")
async def finalize(body: FinalizeBody):
    """Code tinh diem -> Reporter viet nhan xet; Reporter loi thi status = partial (van 200, FR-AI-054)."""
    bind_request(body.session_id)
    started, collector = time.perf_counter(), UsageCollector()
    report = None
    with logged_failure("finalize", started, collector, rag="-"):  # finalize khong dung RAG
        try:
            release = turn_locks.hold(body.session_id)  # 409 turn_in_progress: luot dang chay chua ghi checkpoint
            try:  # giu khoa toi khi ghi xong `done`: next-turn cung luc khong chay tren phien dang tong ket
                snap, stored = await stored_snapshot(session_graph(), body.session_id)  # 503 / 404
                session = stored["session"]
                tracing.start_request("finalize", session_id=safe_session_id(body.session_id),
                                      tags=[session["track"], session["level"]])
                if not stored.get("transcript") and body.end_reason == CANDIDATE_ENDED and \
                        stored["state"].get("phase") != "done":  # bam ket thuc truoc khi tra loi: van chot phien
                    await record_finalize_end(session_graph(), body.session_id,
                                              {**stored["state"], "phase": "done", "end_reason": CANDIDATE_ENDED})
                req = build_finalize_request(body, stored)  # 409 session_no_turns / session_not_done
                wrote = stored["state"].get("phase") != "done"
                if wrote:  # candidate_ended / qua han cung: chot phien truoc (Reporter loi van khong choi tiep duoc)
                    await record_finalize_end(session_graph(), body.session_id, req.state.model_dump(mode="json"))
                if session_graph_enabled():  # node report viet bao cao ngay trong graph, giu khoa phien
                    report = await finalize_run(req, None if wrote else snap, collector)
            finally:
                release()
        except BaseException:
            trace_on_early_error("finalize", body.session_id)
            raise
        # phase 05: topic da doi (state.swaps) thanh plan thuc te truoc khi cham diem / bao cao; plan cu y nguyen
        if report is None:
            req = req.model_copy(update={"plan": effective_plan(req.plan, req.state)})
            report = await get_reporter().report(req, collector)
        usage = collector.to_metadata()
        report.setdefault("meta", {})["fallbacks"] = usage["fallbacks"]
        # FR-AI-080: token cua Reporter de tinh chi phi ca phien (start + next-turn + finalize)
        report["metadata"] = {**report.get("metadata", {}), "usage": usage["usage"],
                              "latency_ms_by_agent": usage["latency_ms"]}
        tracing.set_output(report.get("overall"))
    finish_request("finalize", started, collector, "ok", rag="-")
    return report
