from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedException, ValidationException
from app.db.session import get_db
from app.services.auth import AuthenticatedUser, TokenService, WeChatAuthService
from app.services.ocr.base import OCRService
from app.services.ocr.mock import MockOCRService
from app.services.ocr.rapidocr import RapidOCRService
from app.services.parsing.parser import ParsingService
from app.services.pdf.service import PDFService
from app.services.storage.base import StorageService
from app.services.storage.cos import COSStorageService
from app.services.storage.local import LocalStorageService
from app.services.voucher_task_service import VoucherTaskService

bearer_scheme = HTTPBearer(auto_error=False)


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    provider = settings.storage_provider.lower()
    if provider == "local":
        return LocalStorageService(root=settings.local_storage_path, max_upload_mb=settings.max_upload_mb)
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
    return TokenService(
        secret_key=settings.auth_secret_key,
        issuer=settings.auth_issuer,
        expires_in_seconds=settings.auth_token_expire_minutes * 60,
    )


def get_wechat_auth_service(
    settings: Settings = Depends(get_settings),
    token_service: TokenService = Depends(get_token_service),
) -> WeChatAuthService:
    return WeChatAuthService(settings=settings, token_service=token_service)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token_service: TokenService = Depends(get_token_service),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedException(message="Bearer token is required")
    return token_service.verify_access_token(credentials.credentials)


def get_voucher_task_service(
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
    ocr_service: OCRService = Depends(get_ocr_service),
    parsing_service: ParsingService = Depends(get_parsing_service),
    pdf_service: PDFService = Depends(get_pdf_service),
) -> VoucherTaskService:
    return VoucherTaskService(
        db=db,
        storage_service=storage_service,
        ocr_service=ocr_service,
        parsing_service=parsing_service,
        pdf_service=pdf_service,
    )
