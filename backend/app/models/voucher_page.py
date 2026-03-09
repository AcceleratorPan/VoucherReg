from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _page_id() -> str:
    return f"vp_{uuid.uuid4().hex[:12]}"


class VoucherPage(Base):
    __tablename__ = "voucher_page"
    __table_args__ = (UniqueConstraint("task_id", "page_index", name="uq_voucher_page_task_index"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=_page_id)
    task_id: Mapped[str] = mapped_column(String(24), ForeignKey("voucher_task.id", ondelete="CASCADE"), nullable=False)

    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumb_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_first_page: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task = relationship("VoucherTask", back_populates="pages")
