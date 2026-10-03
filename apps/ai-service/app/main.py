"""AI Interview Service (mock). Contract: docs/architecture/ai-integration.md."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import mock_logic
from .schemas import (
    FinalizeRequest,
    FinalizeResponse,
    HealthResponse,
    NextTurnRequest,
    NextTurnResponse,
    StartRequest,
    StartResponse,
)

app = FastAPI(title="AI Interview Service (Mock)", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    # Dong bo format loi voi contract: { error, message, details }
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    return JSONResponse(
        status_code=422,
        content={
            "error": "invalid_request",
            "message": f"{field}: {first.get('msg', 'invalid request')}",
            "details": {"errors": jsonable(exc.errors())},
        },
    )


def jsonable(errors):
    return [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in errors]


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="healthy", version=mock_logic.MODEL_VERSION, model_loaded=False)


@app.post("/api/start", response_model=StartResponse)
def start(req: StartRequest):
    return mock_logic.mock_start(req)


@app.post("/api/next-turn", response_model=NextTurnResponse)
def next_turn(req: NextTurnRequest):
    return mock_logic.mock_next_turn(req)


@app.post("/api/finalize", response_model=FinalizeResponse)
def finalize(req: FinalizeRequest):
    return mock_logic.mock_finalize(req)
