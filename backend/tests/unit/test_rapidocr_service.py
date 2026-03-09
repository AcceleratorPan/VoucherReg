import asyncio
import types

import pytest

from app.core.exceptions import AppException, ValidationException
from app.services.ocr.rapidocr import RapidOCRService


class _RapidOutput:
    def __init__(self, txts):
        self.txts = txts


class _FakeRapidOCR:
    def __call__(self, image_bytes, **kwargs):  # noqa: ANN001, ANN003
        _ = image_bytes
        _ = kwargs
        return _RapidOutput(txts=("核算单位: 测试公司", "凭证号: 记-12"))


def test_rapidocr_success(sample_image_bytes: bytes, monkeypatch) -> None:
    fake_module = types.SimpleNamespace(RapidOCR=lambda: _FakeRapidOCR())
    monkeypatch.setattr("app.services.ocr.rapidocr.importlib.import_module", lambda _: fake_module)

    service = RapidOCRService(text_score=0.5)
    text = asyncio.run(service.recognize(sample_image_bytes))

    assert "核算单位: 测试公司" in text
    assert "凭证号: 记-12" in text


def test_rapidocr_missing_dependency(sample_image_bytes: bytes, monkeypatch) -> None:
    def _raise(_name: str):
        raise ModuleNotFoundError("rapidocr missing")

    monkeypatch.setattr("app.services.ocr.rapidocr.importlib.import_module", _raise)

    service = RapidOCRService()
    with pytest.raises(AppException) as exc:
        asyncio.run(service.recognize(sample_image_bytes))

    assert exc.value.code == "OCR_DEPENDENCY_MISSING"


def test_rapidocr_empty_input() -> None:
    service = RapidOCRService()

    with pytest.raises(ValidationException):
        asyncio.run(service.recognize(b""))


def test_rapidocr_empty_result(sample_image_bytes: bytes, monkeypatch) -> None:
    class _EmptyRapidOCR:
        def __call__(self, image_bytes, **kwargs):  # noqa: ANN001, ANN003
            _ = image_bytes
            _ = kwargs
            return _RapidOutput(txts=())

    fake_module = types.SimpleNamespace(RapidOCR=lambda: _EmptyRapidOCR())
    monkeypatch.setattr("app.services.ocr.rapidocr.importlib.import_module", lambda _: fake_module)

    service = RapidOCRService()
    with pytest.raises(AppException) as exc:
        asyncio.run(service.recognize(sample_image_bytes))

    assert exc.value.code == "OCR_EMPTY_RESULT"
