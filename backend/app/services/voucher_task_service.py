from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ConflictException, NotFoundException, ValidationException
from app.models import VoucherPage, VoucherTask, VoucherTaskStatus
from app.schemas.voucher_task import ConfirmGenerateRequest
from app.services.ocr.base import OCRService
from app.services.parsing.parser import ParsedVoucherResult, ParsingService
from app.services.pdf.service import PDFService
from app.services.storage.base import StorageService
from app.utils.filename import build_voucher_filename


class VoucherTaskService:
    def __init__(
        self,
        db: Session,
        storage_service: StorageService,
        ocr_service: OCRService,
        parsing_service: ParsingService,
        pdf_service: PDFService,
    ) -> None:
        self.db = db
        self.storage_service = storage_service
        self.ocr_service = ocr_service
        self.parsing_service = parsing_service
        self.pdf_service = pdf_service

    async def create_task(self, user_id: str) -> dict:
        user_id = self._require_user_id(user_id)
        task = VoucherTask(user_id=user_id, status=VoucherTaskStatus.DRAFT.value, page_count=0)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return self._task_to_dict(task)

    async def upload_page(self, user_id: str, task_id: str, page_index: int | None, upload_file) -> dict:
        normalized_user_id = self._require_user_id(user_id)
        task = self._get_task(task_id, normalized_user_id)
        if task.status != VoucherTaskStatus.DRAFT.value:
            raise ConflictException(message="Pages can only be uploaded while task is in draft status")

        existing_count = self._count_pages(task_id)
        if page_index is None:
            page_index = self._next_page_index(task_id)
        elif page_index < 0:
            raise ValidationException(message="pageIndex must be >= 0")

        if existing_count == 0 and page_index != 0:
            raise ValidationException(message="The first uploaded page must use pageIndex=0")

        existing_page = self.db.scalar(
            select(VoucherPage).where(VoucherPage.task_id == task_id, VoucherPage.page_index == page_index)
        )
        if existing_page:
            raise ConflictException(message="pageIndex already exists for this task", detail={"pageIndex": page_index})

        stored_file = await self.storage_service.save_upload(
            user_id=normalized_user_id,
            task_id=task_id,
            page_index=page_index,
            upload_file=upload_file,
        )

        page = VoucherPage(
            task_id=task_id,
            page_index=page_index,
            image_path=stored_file.path,
            image_url=stored_file.url,
            thumb_url=None,
            is_first_page=(page_index == 0),
            width=stored_file.width,
            height=stored_file.height,
        )

        self.db.add(page)
        task.page_count = existing_count + 1
        self.db.commit()
        self.db.refresh(page)
        self.db.refresh(task)

        return self._page_to_dict(page)

    async def finish_upload(self, user_id: str, task_id: str) -> dict:
        task = self._get_task(task_id, self._require_user_id(user_id))
        if task.status != VoucherTaskStatus.DRAFT.value:
            raise ConflictException(message="finish-upload is allowed only in draft status")
        if task.page_count < 1:
            raise ValidationException(message="At least one page is required before finish-upload")

        task.status = VoucherTaskStatus.UPLOADED.value
        self.db.commit()
        self.db.refresh(task)

        return {
            "task_id": task.id,
            "status": task.status,
            "page_count": task.page_count,
        }

    async def recognize(self, user_id: str, task_id: str) -> dict:
        task = self._get_task(task_id, self._require_user_id(user_id))
        if task.status != VoucherTaskStatus.UPLOADED.value:
            raise ConflictException(message="recognize is allowed only after finish-upload")

        first_page = self.db.scalar(
            select(VoucherPage)
            .where(VoucherPage.task_id == task_id)
            .order_by(VoucherPage.page_index.asc())
            .limit(1)
        )
        if not first_page:
            raise ValidationException(message="No pages found for recognition")

        try:
            image_bytes = await self.storage_service.read_bytes(first_page.image_path)
            raw_text = await self.ocr_service.recognize(image_bytes=image_bytes, image_url=first_page.image_url)
            parsed: ParsedVoucherResult = self.parsing_service.parse(raw_text)
        except AppException:
            task.status = VoucherTaskStatus.FAILED.value
            self.db.commit()
            raise
        except Exception as exc:
            task.status = VoucherTaskStatus.FAILED.value
            self.db.commit()
            raise AppException(
                status_code=500,
                code="OCR_FAILED",
                message="OCR recognition failed",
                detail={"error": str(exc)},
            ) from exc

        task.subject = parsed.subject
        task.voucher_month = parsed.month
        task.voucher_no = parsed.voucher_no
        task.file_name = parsed.file_name_preview
        task.raw_ocr_text = raw_text
        task.confidence = parsed.confidence
        task.status = VoucherTaskStatus.RECOGNIZED.value

        self.db.commit()
        self.db.refresh(task)

        return {
            "task_id": task.id,
            "subject": parsed.subject,
            "month": parsed.month,
            "voucher_no": parsed.voucher_no,
            "file_name_preview": parsed.file_name_preview,
            "confidence": parsed.confidence,
            "needs_user_review": parsed.needs_user_review,
        }

    async def confirm_generate(self, user_id: str, task_id: str, payload: ConfirmGenerateRequest) -> dict:
        normalized_user_id = self._require_user_id(user_id)
        task = self._get_task(task_id, normalized_user_id)
        if task.status != VoucherTaskStatus.RECOGNIZED.value:
            raise ConflictException(message="confirm-generate is allowed only in recognized status")

        subject = payload.subject or task.subject
        month = payload.month or task.voucher_month
        voucher_no = payload.voucher_no or task.voucher_no

        if not subject or not month or not voucher_no:
            raise ValidationException(message="subject, month, and voucherNo are required to generate PDF")

        pages = self.db.scalars(
            select(VoucherPage).where(VoucherPage.task_id == task_id).order_by(VoucherPage.page_index.asc())
        ).all()
        if not pages:
            raise ValidationException(message="No pages found for PDF generation")

        task.subject = subject
        task.voucher_month = month
        task.voucher_no = voucher_no
        task.status = VoucherTaskStatus.CONFIRMED.value
        self.db.commit()
        self.db.refresh(task)

        try:
            ordered_images = [await self.storage_service.read_bytes(page.image_path) for page in pages]
            pdf_bytes = await self.pdf_service.generate_pdf(ordered_images)

            final_file_name = build_voucher_filename(subject, month, voucher_no)
            safe_user_id = self._safe_user_id(normalized_user_id)
            pdf_relative_path = f"{safe_user_id}/tasks/{task_id}/result/{final_file_name}"
            pdf_url = await self.storage_service.save_bytes(pdf_relative_path, pdf_bytes, content_type="application/pdf")

            task.file_name = final_file_name
            task.pdf_url = pdf_url
            task.status = VoucherTaskStatus.PDF_GENERATED.value
        except Exception:
            task.status = VoucherTaskStatus.FAILED.value
            self.db.commit()
            raise

        self.db.commit()
        self.db.refresh(task)

        return {
            "task_id": task.id,
            "status": task.status,
            "file_name": task.file_name,
            "pdf_url": task.pdf_url,
        }

    async def list_tasks(self, user_id: str, limit: int, offset: int) -> dict:
        normalized_user_id = self._require_user_id(user_id)
        items = self.db.scalars(
            select(VoucherTask)
            .where(VoucherTask.user_id == normalized_user_id)
            .order_by(VoucherTask.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        total = self.db.scalar(select(func.count()).select_from(VoucherTask).where(VoucherTask.user_id == normalized_user_id)) or 0

        return {
            "items": [self._task_to_dict(item) for item in items],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def get_task_detail(self, user_id: str, task_id: str) -> dict:
        task = self._get_task(task_id, self._require_user_id(user_id))
        pages = self.db.scalars(
            select(VoucherPage).where(VoucherPage.task_id == task_id).order_by(VoucherPage.page_index.asc())
        ).all()

        data = self._task_to_dict(task)
        data["raw_ocr_text"] = task.raw_ocr_text
        data["pages"] = [self._page_to_dict(page) for page in pages]
        return data

    async def delete_task(self, user_id: str, task_id: str) -> dict:
        normalized_user_id = self._require_user_id(user_id)
        task = self._get_task(task_id, normalized_user_id)

        self.db.delete(task)
        self.db.commit()

        safe_user_id = self._safe_user_id(normalized_user_id)
        await self.storage_service.delete_prefix(f"{safe_user_id}/tasks/{task_id}")
        return {"task_id": task_id, "deleted": True}

    async def clear_history(self, user_id: str) -> dict:
        normalized_user_id = self._require_user_id(user_id)
        tasks = self.db.scalars(select(VoucherTask).where(VoucherTask.user_id == normalized_user_id)).all()
        task_ids = [task.id for task in tasks]
        deleted_count = len(task_ids)

        for task in tasks:
            self.db.delete(task)
        self.db.commit()

        safe_user_id = self._safe_user_id(normalized_user_id)
        for task_id in task_ids:
            await self.storage_service.delete_prefix(f"{safe_user_id}/tasks/{task_id}")

        return {"user_id": normalized_user_id, "deleted_count": deleted_count}

    def _get_task(self, task_id: str, user_id: str | None = None) -> VoucherTask:
        task = self.db.get(VoucherTask, task_id)
        if not task:
            raise NotFoundException(message="Voucher task not found", detail={"taskId": task_id})
        if user_id is not None and task.user_id != user_id:
            raise NotFoundException(message="Voucher task not found for user", detail={"taskId": task_id, "userId": user_id})
        return task

    def _next_page_index(self, task_id: str) -> int:
        max_index = self.db.scalar(select(func.max(VoucherPage.page_index)).where(VoucherPage.task_id == task_id))
        return 0 if max_index is None else int(max_index) + 1

    def _count_pages(self, task_id: str) -> int:
        return self.db.scalar(select(func.count()).where(VoucherPage.task_id == task_id)) or 0

    @staticmethod
    def _require_user_id(user_id: str | None) -> str:
        if not user_id or not user_id.strip():
            raise ValidationException(message="userId is required")
        return user_id.strip()

    @staticmethod
    def _safe_user_id(user_id: str) -> str:
        cleaned = user_id.strip().replace("\\", "_").replace("/", "_")
        return cleaned or "unknown-user"

    @staticmethod
    def _task_to_dict(task: VoucherTask) -> dict:
        return {
            "task_id": task.id,
            "user_id": task.user_id,
            "subject": task.subject,
            "month": task.voucher_month,
            "voucher_no": task.voucher_no,
            "file_name": task.file_name,
            "pdf_url": task.pdf_url,
            "status": task.status,
            "page_count": task.page_count,
            "confidence": task.confidence,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    @staticmethod
    def _page_to_dict(page: VoucherPage) -> dict:
        return {
            "page_id": page.id,
            "task_id": page.task_id,
            "page_index": page.page_index,
            "image_url": page.image_url,
            "thumb_url": page.thumb_url,
            "is_first_page": page.is_first_page,
            "width": page.width,
            "height": page.height,
            "created_at": page.created_at,
            "updated_at": page.updated_at,
        }
