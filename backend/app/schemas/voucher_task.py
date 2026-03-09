from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.base import APIModel


class VoucherPageResponse(APIModel):
    page_id: str
    task_id: str
    page_index: int
    image_url: str
    thumb_url: str | None = None
    is_first_page: bool
    width: int | None = None
    height: int | None = None
    created_at: datetime
    updated_at: datetime


class CreateVoucherTaskRequest(APIModel):
    user_id: str | None = None


class VoucherTaskResponse(APIModel):
    task_id: str
    user_id: str | None = None
    subject: str | None = None
    month: str | None = None
    voucher_no: str | None = None
    file_name: str | None = None
    pdf_url: str | None = None
    status: str
    page_count: int
    confidence: float | None = None
    created_at: datetime
    updated_at: datetime


class VoucherTaskDetailResponse(VoucherTaskResponse):
    raw_ocr_text: str | None = None
    pages: list[VoucherPageResponse] = Field(default_factory=list)


class FinishUploadResponse(APIModel):
    task_id: str
    status: str
    page_count: int


class RecognizeResponse(APIModel):
    task_id: str
    subject: str | None = None
    month: str | None = None
    voucher_no: str | None = None
    file_name_preview: str
    confidence: float
    needs_user_review: bool


class FirstVoucherImageResponse(APIModel):
    task_id: str
    page_id: str
    page_index: int
    image_url: str
    thumb_url: str | None = None
    is_first_page: bool


class ConfirmGenerateRequest(APIModel):
    subject: str | None = None
    month: str | None = None
    voucher_no: str | None = None


class ConfirmGenerateResponse(APIModel):
    task_id: str
    status: str
    file_name: str
    pdf_url: str


class DownloadLinkResponse(APIModel):
    task_id: str
    file_name: str
    content_type: str
    download_url: str
    expires_at: datetime


class BatchDownloadLinkRequest(APIModel):
    task_ids: list[str] = Field(min_length=1)


class BatchDownloadLinkResponse(APIModel):
    task_ids: list[str]
    file_name: str
    content_type: str
    download_url: str
    expires_at: datetime


class VoucherTaskListResponse(APIModel):
    items: list[VoucherTaskResponse]
    total: int
    offset: int
    limit: int


class DeleteTaskResponse(APIModel):
    task_id: str
    deleted: bool


class ClearHistoryResponse(APIModel):
    user_id: str
    deleted_count: int


class ManualGenerateRequest(APIModel):
    subject: str
    month: str
    voucher_no: str


class ManualGenerateResponse(APIModel):
    task_id: str
    status: str
    file_name: str
    pdf_url: str
