from __future__ import annotations

from fastapi import UploadFile

from app.core.exceptions import AppException
from app.services.storage.base import StoredFile


class COSStorageService:
    """Placeholder COS adapter for future direct cloud storage support."""

    async def save_upload(self, user_id: str, task_id: str, page_index: int, upload_file: UploadFile) -> StoredFile:  # noqa: ARG002
        raise AppException(status_code=501, code="COS_NOT_IMPLEMENTED", message="COS storage is not implemented yet")

    async def save_bytes(self, relative_path: str, data: bytes, content_type: str | None = None) -> str:  # noqa: ARG002
        raise AppException(status_code=501, code="COS_NOT_IMPLEMENTED", message="COS storage is not implemented yet")

    async def read_bytes(self, path: str) -> bytes:  # noqa: ARG002
        raise AppException(status_code=501, code="COS_NOT_IMPLEMENTED", message="COS storage is not implemented yet")

    async def delete_prefix(self, prefix: str) -> None:  # noqa: ARG002
        raise AppException(status_code=501, code="COS_NOT_IMPLEMENTED", message="COS storage is not implemented yet")
