"""Document ingestion storage.

Revision ID: 0003_document_ingestion
Revises: 0002_invite_auth
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_document_ingestion"
down_revision: str | None = "0002_invite_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("review_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("extraction_state", sa.String(length=32), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("ocr_used", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index("ix_documents_session_id", "documents", ["session_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_extraction_state", "documents", ["extraction_state"])

    op.create_table(
        "document_segments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "document_id",
            "ordinal",
            name="uq_document_segments_document_ordinal",
        ),
    )
    op.create_index("ix_document_segments_document_id", "document_segments", ["document_id"])


def downgrade() -> None:
    op.drop_table("document_segments")
    op.drop_table("documents")
