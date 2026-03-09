from __future__ import annotations

from typing import Protocol


class OCRService(Protocol):
    async def recognize(self, image_bytes: bytes, image_url: str | None = None) -> str:
        ...
