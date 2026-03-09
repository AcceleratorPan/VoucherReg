from __future__ import annotations

from pathlib import Path
import shutil

from fastapi import UploadFile

from app.core.exceptions import ValidationException
from app.services.image.scanner import ImageScanner, OpenCVDocumentScanner
from app.services.storage.base import StoredFile


class LocalStorageService:
    def __init__(self, root: Path, max_upload_mb: int = 15, scanner: ImageScanner | None = None) -> None:
        self.root = root
        self.max_upload_bytes = max_upload_mb * 1024 * 1024
        self.scanner = scanner or OpenCVDocumentScanner()
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, user_id: str, task_id: str, page_index: int, upload_file: UploadFile) -> StoredFile:
        self._validate_upload_content_type(upload_file)
        data = await upload_file.read()
        self._validate_upload_size(data)
        processed = self.scanner.scan(data)

        safe_user_id = self._safe_user_id(user_id)
        relative_path = f"{safe_user_id}/tasks/{task_id}/pages/{page_index}{processed.extension}"
        output_path = self.root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(processed.data)

        return StoredFile(
            path=relative_path,
            url=self._as_url(relative_path),
            width=processed.width,
            height=processed.height,
        )

    async def save_bytes(self, relative_path: str, data: bytes, content_type: str | None = None) -> str:  # noqa: ARG002
        clean_relative = relative_path.lstrip("/")
        output_path = self.root / clean_relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
        return self._as_url(clean_relative)

    async def read_bytes(self, path: str) -> bytes:
        clean_path = path.strip()
        if clean_path.startswith("/files/"):
            clean_path = clean_path[len("/files/") :]
        file_path = self.root / clean_path.lstrip("/")
        return file_path.read_bytes()

    async def delete_prefix(self, prefix: str) -> None:
        clean_prefix = prefix.strip().lstrip("/")
        target_path = self.root / clean_prefix
        if target_path.exists():
            shutil.rmtree(target_path, ignore_errors=True)

    def _validate_upload_size(self, data: bytes) -> None:
        if not data:
            raise ValidationException(message="Uploaded file is empty")
        if len(data) > self.max_upload_bytes:
            raise ValidationException(
                message=f"Uploaded file exceeds {self.max_upload_bytes // (1024 * 1024)}MB limit"
            )

    @staticmethod
    def _validate_upload_content_type(upload_file: UploadFile) -> None:
        content_type = (upload_file.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise ValidationException(
                message="Only image files are supported",
                detail={"contentType": upload_file.content_type},
            )

    @staticmethod
    def _as_url(relative_path: str) -> str:
        return "/files/" + relative_path.replace("\\", "/")

    @staticmethod
    def _safe_user_id(user_id: str) -> str:
        cleaned = user_id.strip().replace("\\", "_").replace("/", "_")
        return cleaned or "unknown-user"
