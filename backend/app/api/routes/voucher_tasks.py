from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.deps import get_current_user, get_voucher_task_service
from app.schemas.voucher_task import (
    ClearHistoryResponse,
    ConfirmGenerateRequest,
    ConfirmGenerateResponse,
    DeleteTaskResponse,
    FinishUploadResponse,
    RecognizeResponse,
    VoucherPageResponse,
    VoucherTaskDetailResponse,
    VoucherTaskListResponse,
    VoucherTaskResponse,
)
from app.services.auth import AuthenticatedUser
from app.services.voucher_task_service import VoucherTaskService

router = APIRouter(prefix="/voucher-tasks")


@router.post("", response_model=VoucherTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_voucher_task(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherTaskResponse:
    task = await service.create_task(user_id=current_user.user_id)
    return VoucherTaskResponse.model_validate(task)


@router.post("/{task_id}/pages", response_model=VoucherPageResponse)
async def upload_voucher_page(
    task_id: str,
    file: UploadFile = File(...),
    page_index: int | None = Form(default=None, alias="pageIndex"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherPageResponse:
    page = await service.upload_page(
        user_id=current_user.user_id,
        task_id=task_id,
        page_index=page_index,
        upload_file=file,
    )
    return VoucherPageResponse.model_validate(page)


@router.post("/{task_id}/finish-upload", response_model=FinishUploadResponse)
async def finish_upload(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> FinishUploadResponse:
    result = await service.finish_upload(user_id=current_user.user_id, task_id=task_id)
    return FinishUploadResponse.model_validate(result)


@router.post("/{task_id}/recognize", response_model=RecognizeResponse)
async def recognize_task(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> RecognizeResponse:
    result = await service.recognize(user_id=current_user.user_id, task_id=task_id)
    return RecognizeResponse.model_validate(result)


@router.post("/{task_id}/confirm-generate", response_model=ConfirmGenerateResponse)
async def confirm_generate(
    task_id: str,
    payload: ConfirmGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> ConfirmGenerateResponse:
    result = await service.confirm_generate(user_id=current_user.user_id, task_id=task_id, payload=payload)
    return ConfirmGenerateResponse.model_validate(result)


@router.get("", response_model=VoucherTaskListResponse)
async def list_voucher_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherTaskListResponse:
    result = await service.list_tasks(user_id=current_user.user_id, limit=limit, offset=offset)
    return VoucherTaskListResponse.model_validate(result)


@router.get("/{task_id}", response_model=VoucherTaskDetailResponse)
async def get_voucher_task_detail(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> VoucherTaskDetailResponse:
    result = await service.get_task_detail(user_id=current_user.user_id, task_id=task_id)
    return VoucherTaskDetailResponse.model_validate(result)


@router.delete("/{task_id}", response_model=DeleteTaskResponse)
async def delete_voucher_task(
    task_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> DeleteTaskResponse:
    result = await service.delete_task(user_id=current_user.user_id, task_id=task_id)
    return DeleteTaskResponse.model_validate(result)


@router.delete("", response_model=ClearHistoryResponse)
async def clear_voucher_history(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> ClearHistoryResponse:
    result = await service.clear_history(user_id=current_user.user_id)
    return ClearHistoryResponse.model_validate(result)
