from __future__ import annotations

from app.schemas.base import APIModel


class ErrorResponse(APIModel):
    code: str
    message: str
    detail: dict
