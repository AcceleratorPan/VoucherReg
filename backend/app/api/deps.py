from __future__ import annotations

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationException
from app.db.session import get_db
from app.services.auth import TokenService
from app.services.image.scanner import OpenCVDocumentScanner
from app.services.ocr.base import OCRService
from app.services.ocr.mock import MockOCRService
from app.services.ocr.rapidocr import RapidOCRService
from app.services.parsing.parser import ParsingService
from app.services.pdf.service import PDFService
from app.services.storage.base import StorageService
from app.services.storage.cos import COSStorageService
from app.services.storage.local import LocalStorageService
from app.services.voucher_task_service import VoucherTaskService


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    provider = settings.storage_provider.lower()
    if provider == "local":
        return LocalStorageService(
            root=settings.local_storage_path,
            max_upload_mb=settings.max_upload_mb,
            scanner=OpenCVDocumentScanner(max_edge=settings.document_scan_max_edge),
        )
    if provider == "cos":
        return COSStorageService()
    raise ValidationException(message=f"Unsupported storage provider: {settings.storage_provider}")


def get_ocr_service(settings: Settings = Depends(get_settings)) -> OCRService:
    provider = settings.ocr_provider.lower()
    if provider == "rapidocr":
        return RapidOCRService(
            text_score=settings.rapidocr_text_score,
            use_det=settings.rapidocr_use_det,
            use_cls=settings.rapidocr_use_cls,
            use_rec=settings.rapidocr_use_rec,
        )
    if provider == "mock":
        return MockOCRService()
    raise ValidationException(message=f"Unsupported OCR provider: {settings.ocr_provider}")


def get_parsing_service() -> ParsingService:
    return ParsingService()


def get_pdf_service() -> PDFService:
    return PDFService()


def get_token_service(settings: Settings = Depends(get_settings)) -> TokenService:
    return TokenService(secret_key=settings.auth_secret_key, issuer=settings.auth_issuer)


def get_request_user_id(user_id: str | None = Query(default=None, alias="userId")) -> str | None:
    return user_id


def get_voucher_task_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    storage_service: StorageService = Depends(get_storage_service),
    ocr_service: OCRService = Depends(get_ocr_service),
    parsing_service: ParsingService = Depends(get_parsing_service),
    pdf_service: PDFService = Depends(get_pdf_service),
    token_service: TokenService = Depends(get_token_service),
) -> VoucherTaskService:
    return VoucherTaskService(
        db=db,
        storage_service=storage_service,
        ocr_service=ocr_service,
        parsing_service=parsing_service,
        pdf_service=pdf_service,
        token_service=token_service,
        download_link_expire_seconds=settings.download_link_expire_minutes * 60,
        batch_download_max_tasks=settings.batch_download_max_tasks,
    )
