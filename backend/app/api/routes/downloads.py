from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_voucher_task_service
from app.services.voucher_task_service import VoucherTaskService

router = APIRouter()


@router.get("/downloads/{download_token}", name="consume_download_link")
async def consume_download_link(
    download_token: str,
    service: VoucherTaskService = Depends(get_voucher_task_service),
) -> Response:
    artifact = await service.get_download_artifact(download_token)
    return Response(
        content=artifact.data,
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": _build_content_disposition(artifact.file_name),
            "Cache-Control": "no-store",
        },
    )


def _build_content_disposition(file_name: str) -> str:
    fallback = _ascii_fallback_name(file_name)
    encoded = quote(file_name, safe="")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'


def _ascii_fallback_name(file_name: str) -> str:
    ascii_name = file_name.encode("ascii", "ignore").decode("ascii").replace('"', "").strip()
    if ascii_name:
        return ascii_name
    if file_name.lower().endswith(".zip"):
        return "download.zip"
    return "download.pdf"
