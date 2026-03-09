from __future__ import annotations

from fastapi import APIRouter, Body, Depends, File, Form, Query, Request, UploadFile, status

from app.api.deps import get_request_user_id, get_voucher_task_service
from app.schemas.voucher_task import (
    BatchDownloadLinkRequest,
    BatchDownloadLinkResponse,
    ClearHistoryResponse,
    ConfirmGenerateRequest,
    ConfirmGenerateResponse,
    CreateVoucherTaskRequest,
    DeleteTaskResponse,
    DownloadLinkResponse,
    FinishUploadResponse,
    FirstVoucherImageResponse,
    RecognizeResponse,
    VoucherPageResponse,
    VoucherTaskDetailResponse,
    VoucherTaskListResponse,
    VoucherTaskResponse,
)
from app.services.voucher_task_service import VoucherTaskService

router = APIRouter(prefix="/voucher-tasks")


@router.post("", response_model=VoucherTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_voucher_task(
    payload: CreateVoucherTaskRequest | None = Body(default=None),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherTaskResponse:
    task = await service.create_task(user_id=payload.user_id if payload else None)
    return VoucherTaskResponse.model_validate(task)


@router.post("/{task_id}/pages", response_model=VoucherPageResponse)
async def upload_voucher_page(
    task_id: str,
    file: UploadFile = File(...),
    page_index: int | None = Form(default=None, alias="pageIndex"),
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherPageResponse:
    page = await service.upload_page(
        user_id=user_id,
        task_id=task_id,
        page_index=page_index,
        upload_file=file,
    )
    return VoucherPageResponse.model_validate(page)


@router.post("/{task_id}/finish-upload", response_model=FinishUploadResponse)
async def finish_upload(
    task_id: str,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> FinishUploadResponse:
    result = await service.finish_upload(user_id=user_id, task_id=task_id)
    return FinishUploadResponse.model_validate(result)


@router.post("/{task_id}/recognize", response_model=RecognizeResponse)
async def recognize_task(
    task_id: str,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> RecognizeResponse:
    result = await service.recognize(user_id=user_id, task_id=task_id)
    return RecognizeResponse.model_validate(result)


@router.post("/{task_id}/confirm-generate", response_model=ConfirmGenerateResponse)
async def confirm_generate(
    task_id: str,
    payload: ConfirmGenerateRequest,
    request: Request,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> ConfirmGenerateResponse:
    result = await service.confirm_generate(user_id=user_id, task_id=task_id, payload=payload)
    result = await _attach_download_url(
        request=request,
        service=service,
        user_id=user_id,
        task_data=result,
    )
    return ConfirmGenerateResponse.model_validate(result)


@router.post("/{task_id}/download-link", response_model=DownloadLinkResponse)
async def create_download_link(
    task_id: str,
    request: Request,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> DownloadLinkResponse:
    result = await service.create_download_link(user_id=user_id, task_id=task_id)
    download_url = str(request.url_for("consume_download_link", download_token=result["download_token"]))
    return DownloadLinkResponse.model_validate({**result, "download_url": download_url})


@router.get("/{task_id}/first-image", response_model=FirstVoucherImageResponse)
async def get_first_voucher_image(
    task_id: str,
    request: Request,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> FirstVoucherImageResponse:
    result = await service.get_first_image(user_id=user_id, task_id=task_id)
    result["image_url"] = str(request.url_for("public_file", file_path=result["image_url"].removeprefix("/files/")))
    return FirstVoucherImageResponse.model_validate(result)


@router.post("/batch-download-link", response_model=BatchDownloadLinkResponse)
async def create_batch_download_link(
    payload: BatchDownloadLinkRequest,
    request: Request,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> BatchDownloadLinkResponse:
    result = await service.create_batch_download_link(user_id=user_id, task_ids=payload.task_ids)
    download_url = str(request.url_for("consume_download_link", download_token=result["download_token"]))
    return BatchDownloadLinkResponse.model_validate({**result, "download_url": download_url})


@router.get("", response_model=VoucherTaskListResponse)
async def list_voucher_tasks(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherTaskListResponse:
    result = await service.list_tasks(user_id=user_id, limit=limit, offset=offset)
    result["items"] = [
        await _attach_download_url(
            request=request,
            service=service,
            user_id=user_id,
            task_data=item,
        )
        for item in result["items"]
    ]
    return VoucherTaskListResponse.model_validate(result)


@router.get("/{task_id}", response_model=VoucherTaskDetailResponse)
async def get_voucher_task_detail(
    task_id: str,
    request: Request,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherTaskDetailResponse:
    result = await service.get_task_detail(user_id=user_id, task_id=task_id)
    result = await _attach_download_url(
        request=request,
        service=service,
        user_id=user_id,
        task_data=result,
    )
    return VoucherTaskDetailResponse.model_validate(result)


@router.delete("/{task_id}", response_model=DeleteTaskResponse)
async def delete_voucher_task(
    task_id: str,
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> DeleteTaskResponse:
    result = await service.delete_task(user_id=user_id, task_id=task_id)
    return DeleteTaskResponse.model_validate(result)


@router.delete("", response_model=ClearHistoryResponse)
async def clear_voucher_history(
    user_id: str | None = Depends(get_request_user_id),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> ClearHistoryResponse:
    result = await service.clear_history(user_id=user_id)
    return ClearHistoryResponse.model_validate(result)


async def _attach_download_url(
    request: Request,
    service: VoucherTaskService,
    user_id: str,
    task_data: dict,
) -> dict:
    hydrated = dict(task_data)
    if hydrated.get("status") != "pdf_generated":
        hydrated["pdf_url"] = None
        return hydrated

    download_link = await service.create_download_link(user_id=user_id, task_id=hydrated["task_id"])
    hydrated["pdf_url"] = str(
        request.url_for("consume_download_link", download_token=download_link["download_token"])
    )
    return hydrated
