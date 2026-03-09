from __future__ import annotations

import enum
import uuid

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _task_id() -> str:
    return f"vt_{uuid.uuid4().hex[:12]}"


class VoucherTaskStatus(str, enum.Enum):
    DRAFT = "draft"
    UPLOADED = "uploaded"
    RECOGNIZED = "recognized"
    CONFIRMED = "confirmed"
    PDF_GENERATED = "pdf_generated"
    FAILED = "failed"


class VoucherTask(Base):
    __tablename__ = "voucher_task"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=_task_id)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    voucher_month: Mapped[str | None] = mapped_column(String(7), nullable=True)
    voucher_no: Mapped[str | None] = mapped_column(String(32), nullable=True)

    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(String(24), default=VoucherTaskStatus.DRAFT.value, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    pages = relationship("VoucherPage", back_populates="task", cascade="all, delete-orphan")
