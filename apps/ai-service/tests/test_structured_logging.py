"""Log co cau truc (NFR-AI-OBS02): JSON moi dong, kem session_id / turn_number cua request, khong kem noi dung."""
import asyncio
import json
import logging
import sys

from conftest import parse_sse
from test_interview_flow import play, strong

from app.llm.settings import load_llm_settings
from app.logging_setup import JsonFormatter, RequestContextFilter, bind_request, configure_logging

SECRET = "BI_MAT_CUA_UNG_VIEN"


def json_lines(err: str):
    return [json.loads(line) for line in err.splitlines() if line.startswith("{")]


def record(msg="rag_turn topic=x hits=q1:0.5", exc_info=None):
    r = logging.LogRecord("ai_service.rag", logging.INFO, __file__, 1, msg, (), exc_info)
    RequestContextFilter().filter(r)
    return r


def test_json_line_has_event_and_bound_context():
    bind_request("sess-1", 3)
    try:
        out = json.loads(JsonFormatter().format(record()))
    finally:
        bind_request(None)
    assert out["event"] == "rag_turn" and out["session_id"] == "sess-1" and out["turn_number"] == 3
    assert out["level"] == "INFO" and out["logger"] == "ai_service.rag" and out["ts"].endswith("+00:00")


def test_session_id_from_client_cannot_forge_log_lines():
    bind_request("s1\n{\"level\": \"ERROR\"} " + "x" * 100)
    try:
        sid = record().session_id
    finally:
        bind_request(None)
    assert "\n" not in sid and " " not in sid and len(sid) == 64


def test_exception_keeps_type_and_frames_but_not_its_message():
    try:
        raise ValueError(f"input_value='{SECRET}'")  # vd ValidationError chep lai noi dung dau vao
    except ValueError:
        out = json.loads(JsonFormatter().format(record("stream_failed", sys.exc_info())))
    assert out["exc_type"] == "ValueError" and "test_structured_logging.py" in out["exc"]
    assert SECRET not in json.dumps(out)


def test_llm_io_content_log_is_ignored_outside_dev():
    env = {"LLM_API_KEY": "k", "LOG_LLM_IO": "true"}
    assert load_llm_settings(env).log_io is True
    for app_env in ("staging", "production", "PROD"):
        assert load_llm_settings({**env, "APP_ENV": app_env}).log_io is False


def test_routes_tag_every_line_with_session_and_turn_without_content(client, capsys):
    capsys.readouterr()
    done = parse_sse(client.post("/api/start", json={"session_id": "sess-a", "track": "java_backend",
                                                     "level": "junior"}).text)[-1][1]
    body = {"session_id": "sess-a", "level": "junior", "track": "java_backend", "plan": done["plan"],
            "state": done["state"], "turn_number": 1, "question": done["question"],
            "turn_kind": done["turn"]["turn_kind"], "answer": f"Em làm dự án Java, {SECRET}", "elapsed_seconds": 60}
    parse_sse(client.post("/api/next-turn", json=body).text)
    err = capsys.readouterr().err
    lines = [x for x in json_lines(err) if x["event"] == "request_done"]
    # request_done ghi trong generator SSE: contextvar van theo task cua request khi stream
    assert [(x["session_id"], x["turn_number"]) for x in lines] == [("sess-a", None), ("sess-a", 1)]
    assert SECRET not in err and all("status=ok" in x["msg"] and "rag=off" in x["msg"] for x in lines)


def test_request_done_is_logged_when_route_fails_before_streaming(client, capsys):
    done = parse_sse(client.post("/api/start", json={"session_id": "sess-e", "track": "java_backend",
                                                     "level": "junior"}).text)[-1][1]
    capsys.readouterr()
    body = {"session_id": "sess-e", "level": "junior", "track": "java_backend", "plan": done["plan"],
            "state": {**done["state"], "phase": "done"}, "turn_number": 4, "question": "q", "answer": "a",
            "elapsed_seconds": 60}
    assert client.post("/api/next-turn", json=body).status_code == 409
    line = next(x for x in json_lines(capsys.readouterr().err) if x["event"] == "request_done")
    assert (line["session_id"], line["turn_number"]) == ("sess-e", 4)
    assert "status=error error=ApiError" in line["msg"]


def test_finalize_logs_session(client, capsys):
    plan, state, turns, _ = play(client, "junior", strong)
    capsys.readouterr()
    r = client.post("/api/finalize", json={"session_id": "sess-f", "track": "java_backend", "level": "junior",
                                           "plan": plan, "state": state, "end_reason": "plan_complete",
                                           "duration_s": 1500, "turns": turns})
    assert r.status_code == 200
    line = next(x for x in json_lines(capsys.readouterr().err) if x["event"] == "request_done")
    assert line["session_id"] == "sess-f" and "status=ok" in line["msg"] and "rag=-" in line["msg"]


def test_binding_stays_in_its_request_task():
    """uvicorn chay moi request trong mot task rieng: gia tri gan o request truoc khong sang request sau."""
    async def request(session_id):
        if session_id:
            bind_request(session_id, 2)
        await asyncio.sleep(0)
        return record().session_id

    async def main():
        first = await asyncio.create_task(request("sess-x"))
        return first, await asyncio.create_task(request(None))

    assert asyncio.run(main()) == ("sess-x", None)


def test_log_level_and_text_format_from_env(monkeypatch, capsys):
    logger = logging.getLogger("ai_service")
    try:
        monkeypatch.setenv("LOG_LEVEL", "warning")
        monkeypatch.setenv("LOG_FORMAT", "text")
        configure_logging()
        configure_logging()  # goi lai khong gan them handler
        assert logger.level == logging.WARNING and len(logger.handlers) == 1
        logger.info("hidden_info")
        logger.warning("shown_warning")
        err = capsys.readouterr().err
        assert "hidden_info" not in err and "WARNING ai_service [session=None turn=None] shown_warning" in err
        monkeypatch.setenv("LOG_LEVEL", "10")
        configure_logging()
        assert logger.level == logging.DEBUG
        monkeypatch.setenv("LOG_LEVEL", "LOUD")
        configure_logging()
        assert logger.level == logging.INFO and "log_level_invalid" in capsys.readouterr().err
    finally:
        monkeypatch.delenv("LOG_LEVEL")
        monkeypatch.delenv("LOG_FORMAT")
        configure_logging()
