from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundException

router = APIRouter()

_PUBLIC_FILE_SEGMENTS = {"pages", "thumbs"}


@router.get("/files/{file_path:path}", name="public_file")
async def get_public_file(file_path: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    relative_path = _normalize_public_path(file_path)
    full_path = settings.local_storage_path / relative_path
    if not full_path.is_file():
        raise NotFoundException(message="File not found")
    return FileResponse(full_path)


def _normalize_public_path(file_path: str) -> Path:
    candidate = Path(file_path.strip("/"))
    parts = candidate.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise NotFoundException(message="File not found")
    if not any(segment in _PUBLIC_FILE_SEGMENTS for segment in parts):
        raise NotFoundException(message="File not found")
    if "result" in parts:
        raise NotFoundException(message="File not found")
    return Path(*parts)
