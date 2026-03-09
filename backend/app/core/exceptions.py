from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AppException(Exception):
    status_code: int
    code: str
    message: str
    detail: dict = field(default_factory=dict)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", detail: dict | None = None) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message=message, detail=detail or {})


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed", detail: dict | None = None) -> None:
        super().__init__(status_code=400, code="VALIDATION_ERROR", message=message, detail=detail or {})


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict", detail: dict | None = None) -> None:
        super().__init__(status_code=409, code="CONFLICT", message=message, detail=detail or {})


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized", detail: dict | None = None) -> None:
        super().__init__(status_code=401, code="UNAUTHORIZED", message=message, detail=detail or {})
