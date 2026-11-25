"""Lay Settings / BlazeClient tu app.state (do create_app gan), de test thay bang client gia."""
from fastapi import Request

from .api_error import ApiError
from .blaze_client import BlazeClient
from .config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def require_blaze(request: Request) -> BlazeClient:
    """BlazeClient, hoac 503 provider_unconfigured khi thieu BLAZE_API_KEY. Goi SAU khi kiem dau vao cua request."""
    blaze = request.app.state.blaze
    if blaze is None:
        raise ApiError(503, "provider_unconfigured", "voice-service chưa cấu hình BLAZE_API_KEY")
    return blaze
