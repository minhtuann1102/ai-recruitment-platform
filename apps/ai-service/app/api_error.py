"""Loi API theo contract: { error, message, details } (docs/ai-service/06-api-contract.md)."""
from typing import Optional


class ApiError(Exception):
    def __init__(self, status_code: int, error: str, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details or {}
