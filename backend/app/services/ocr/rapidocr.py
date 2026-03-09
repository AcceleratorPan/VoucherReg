from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

from app.core.exceptions import AppException, ValidationException


class RapidOCRService:
    """Local OCR service based on RapidOCR (PP-OCR Chinese models)."""

    def __init__(
        self,
        text_score: float = 0.5,
        use_det: bool = True,
        use_cls: bool = True,
        use_rec: bool = True,
    ) -> None:
        self.text_score = text_score
        self.use_det = use_det
        self.use_cls = use_cls
        self.use_rec = use_rec
        self._ocr_engine: Any | None = None

    async def recognize(self, image_bytes: bytes, image_url: str | None = None) -> str:  # noqa: ARG002
        if not image_bytes:
            raise ValidationException(message="Input image is empty")

        engine = self._get_engine()
        try:
            result = engine(
                image_bytes,
                use_det=self.use_det,
                use_cls=self.use_cls,
                use_rec=self.use_rec,
                text_score=self.text_score,
            )
        except Exception as exc:  # pragma: no cover - runtime provider failures
            raise AppException(
                status_code=502,
                code="OCR_PROVIDER_ERROR",
                message="RapidOCR recognition failed",
                detail={"error": str(exc)},
            ) from exc

        lines = self._extract_lines(result)
        if not lines:
            raise AppException(
                status_code=502,
                code="OCR_EMPTY_RESULT",
                message="RapidOCR returned an empty result",
            )
        return "\n".join(lines)

    def _get_engine(self) -> Any:
        if self._ocr_engine is not None:
            return self._ocr_engine

        rapidocr_module = self._import_rapidocr_module()
        try:
            rapidocr_cls = getattr(rapidocr_module, "RapidOCR")
        except AttributeError as exc:
            raise AppException(
                status_code=500,
                code="OCR_DEPENDENCY_INVALID",
                message="Installed rapidocr package is missing RapidOCR class",
            ) from exc

        self._ocr_engine = rapidocr_cls()
        return self._ocr_engine

    @staticmethod
    def _import_rapidocr_module() -> ModuleType:
        try:
            return importlib.import_module("rapidocr")
        except ModuleNotFoundError as exc:
            raise AppException(
                status_code=500,
                code="OCR_DEPENDENCY_MISSING",
                message="RapidOCR is not installed. Install with: pip install rapidocr onnxruntime",
            ) from exc

    @classmethod
    def _extract_lines(cls, result: Any) -> list[str]:
        raw_texts: list[str] = []

        if hasattr(result, "txts"):
            txts = getattr(result, "txts")
            if isinstance(txts, (list, tuple)):
                raw_texts.extend([txt for txt in txts if isinstance(txt, str)])

        if not raw_texts and isinstance(result, dict):
            for key in ("txts", "texts", "text"):
                value = result.get(key)
                if isinstance(value, str):
                    raw_texts.append(value)
                elif isinstance(value, (list, tuple)):
                    raw_texts.extend([txt for txt in value if isinstance(txt, str)])

        if not raw_texts and isinstance(result, (list, tuple)):
            for item in result:
                if isinstance(item, str):
                    raw_texts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        raw_texts.append(text)

        # Preserve order while removing duplicates
        lines: list[str] = []
        seen: set[str] = set()
        for text in raw_texts:
            clean = text.strip()
            if clean and clean not in seen:
                seen.add(clean)
                lines.append(clean)
        return lines
