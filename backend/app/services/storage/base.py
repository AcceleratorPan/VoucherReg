from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import UploadFile


@dataclass
class StoredFile:
    path: str
    url: str
    width: int | None = None
    height: int | None = None


class StorageService(Protocol):
    async def save_upload(self, user_id: str, task_id: str, page_index: int, upload_file: UploadFile) -> StoredFile:
        ...

    async def save_bytes(self, relative_path: str, data: bytes, content_type: str | None = None) -> str:
        ...

    async def read_bytes(self, path: str) -> bytes:
        ...

    async def delete_prefix(self, prefix: str) -> None:
        ...
