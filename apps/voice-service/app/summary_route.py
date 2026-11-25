"""POST /api/voice/session-summary: gop chi so trinh bay cac luot voice thanh tong hop phien (FR-011). Khong luu gi."""
from fastapi import APIRouter, Request

from .app_state import get_settings
from .models import SessionDeliverySummary, SummaryRequest
from .session_summary import summarize

router = APIRouter()


@router.post("/api/voice/session-summary", response_model=SessionDeliverySummary)
async def session_summary(body: SummaryRequest, request: Request) -> SessionDeliverySummary:
    return summarize(body.turns, get_settings(request))
