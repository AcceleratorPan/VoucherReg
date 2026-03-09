"""create voucher tables

Revision ID: 0001_create_voucher_tables
Revises: 
Create Date: 2026-03-02 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_voucher_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voucher_task",
        sa.Column("id", sa.String(length=24), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("voucher_month", sa.String(length=7), nullable=True),
        sa.Column("voucher_no", sa.String(length=32), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("pdf_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("raw_ocr_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "voucher_page",
        sa.Column("id", sa.String(length=24), nullable=False),
        sa.Column("task_id", sa.String(length=24), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(length=500), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("thumb_url", sa.String(length=500), nullable=True),
        sa.Column("is_first_page", sa.Boolean(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["voucher_task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "page_index", name="uq_voucher_page_task_index"),
    )


def downgrade() -> None:
    op.drop_table("voucher_page")
    op.drop_table("voucher_task")
